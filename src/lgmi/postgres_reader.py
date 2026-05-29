from __future__ import annotations

import json
import re
from collections.abc import Mapping
from contextlib import contextmanager
from typing import Any

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from lgmi.checkpoint_reader import _preview_bytes, _preview_value, _to_jsonable


_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class PostgresCheckpointReader:
    """Read LangGraph Postgres checkpoint stores without mutating them."""

    def __init__(self, conninfo: str, *, schema: str = "public") -> None:
        if not _IDENTIFIER_RE.fullmatch(schema):
            raise ValueError(f"Unsafe Postgres schema identifier: {schema!r}")
        self.conninfo = conninfo
        self.schema = schema
        self.db_path = f"postgres://{schema}"
        self._serde = JsonPlusSerializer()

    def summary(self) -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                checkpoint_count = self._table_count(cur, "checkpoints")
                write_count = self._table_count(cur, "checkpoint_writes")
                blob_count = self._table_count(cur, "checkpoint_blobs")
                migration_version = self._latest_migration_version(cur)
                cur.execute(
                    self._sql(
                        """
                        select thread_id,
                               count(*) as checkpoint_count,
                               min(checkpoint_id) as first_checkpoint_id,
                               max(checkpoint_id) as latest_checkpoint_id
                        from {checkpoints}
                        group by thread_id
                        order by max(checkpoint_id) desc
                        """
                    )
                )
                thread_rows = cur.fetchall()
                cur.execute(
                    self._sql(
                        """
                        select distinct checkpoint_ns
                        from {checkpoints}
                        order by checkpoint_ns
                        """
                    )
                )
                namespaces = [row["checkpoint_ns"] for row in cur.fetchall()]

        return {
            "db_path": self.db_path,
            "exists": True,
            "file_size_bytes": None,
            "checkpoint_count": checkpoint_count,
            "write_count": write_count,
            "blob_count": blob_count,
            "thread_count": len(thread_rows),
            "diagnostics_count": 0,
            "diagnostics_count_mode": "not_scanned_for_postgres",
            "checkpoint_namespaces": namespaces,
            "checkpoint_migration_version": migration_version,
            "adapter": "LangGraph Postgres Checkpointer",
            "threads": [dict(row) for row in thread_rows],
        }

    def list_threads(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    self._sql(
                        """
                        select c.thread_id,
                               count(*) as checkpoint_count,
                               min(c.checkpoint_id) as first_checkpoint_id,
                               max(c.checkpoint_id) as latest_checkpoint_id,
                               count(distinct c.checkpoint_ns) as namespace_count,
                               coalesce(w.write_count, 0) as write_count
                        from {checkpoints} c
                        left join (
                            select thread_id, count(*) as write_count
                            from {checkpoint_writes}
                            group by thread_id
                        ) w on w.thread_id = c.thread_id
                        group by c.thread_id, w.write_count
                        order by max(c.checkpoint_id) desc
                        """
                    )
                )
                rows = cur.fetchall()

                threads: list[dict[str, Any]] = []
                for row in rows:
                    latest = self._fetch_checkpoint_row(
                        cur,
                        str(row["thread_id"]),
                        str(row["latest_checkpoint_id"]),
                        include_checkpoint=False,
                    )
                    item = dict(row)
                    item["latest_checkpoint"] = latest
                    item["checkpoint_namespaces"] = self._thread_namespaces(
                        cur, str(row["thread_id"])
                    )
                    threads.append(item)
                return threads

    def list_checkpoints(
        self, thread_id: str, checkpoint_ns: str | None = None
    ) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                namespace_sql, params = self._namespace_filter(checkpoint_ns)
                cur.execute(
                    self._sql(
                        f"""
                        select thread_id, checkpoint_ns, checkpoint_id,
                               parent_checkpoint_id, type, checkpoint, metadata
                        from {{checkpoints}}
                        where thread_id = %s
                        {namespace_sql}
                        order by checkpoint_id
                        """
                    ),
                    (thread_id, *params),
                )
                return [
                    self._checkpoint_row_to_dict(cur, row, include_checkpoint=False)
                    for row in cur.fetchall()
                ]

    def get_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str,
        checkpoint_ns: str | None = None,
    ) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                return self._fetch_checkpoint_row(
                    cur,
                    thread_id,
                    checkpoint_id,
                    checkpoint_ns=checkpoint_ns,
                    include_checkpoint=True,
                )

    def list_writes(
        self,
        thread_id: str,
        checkpoint_id: str,
        checkpoint_ns: str | None = None,
    ) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                writes_checkpoint_id = self._incoming_writes_checkpoint_id(
                    cur, thread_id, checkpoint_id, checkpoint_ns
                )
                task_path_expr = "task_path" if self._has_column(cur, "checkpoint_writes", "task_path") else "'' as task_path"
                namespace_sql, params = self._namespace_filter(checkpoint_ns)
                cur.execute(
                    self._sql(
                        f"""
                        select thread_id, checkpoint_ns, checkpoint_id,
                               task_id, {task_path_expr}, idx, channel, type, blob
                        from {{checkpoint_writes}}
                        where thread_id = %s and checkpoint_id = %s
                        {namespace_sql}
                        order by task_path, task_id, idx
                        """
                    ),
                    (thread_id, writes_checkpoint_id, *params),
                )
                return [self._write_row_to_dict(row) for row in cur.fetchall()]

    @contextmanager
    def _connect(self):
        psycopg, dict_row, _ = _postgres_modules()
        with psycopg.connect(self.conninfo, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("BEGIN READ ONLY")
            try:
                with conn.cursor() as cur:
                    self._ensure_schema(cur)
                yield conn
            finally:
                with conn.cursor() as cur:
                    cur.execute("ROLLBACK")

    def _ensure_schema(self, cur: Any) -> None:
        required = {
            "checkpoints": {"thread_id", "checkpoint_ns", "checkpoint_id", "parent_checkpoint_id", "checkpoint", "metadata"},
            "checkpoint_blobs": {"thread_id", "checkpoint_ns", "channel", "version", "type", "blob"},
            "checkpoint_writes": {"thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", "channel", "type", "blob"},
        }
        missing_tables: list[str] = []
        missing_columns: list[str] = []
        for table_name, required_columns in required.items():
            columns = self._columns(cur, table_name)
            if not columns:
                missing_tables.append(table_name)
                continue
            missing = sorted(required_columns - columns)
            missing_columns.extend(f"{table_name}.{column}" for column in missing)

        if missing_tables:
            names = ", ".join(missing_tables)
            raise ValueError(f"Missing LangGraph Postgres checkpoint table(s): {names}")
        if missing_columns:
            names = ", ".join(missing_columns)
            if "checkpoints.checkpoint_id" in missing_columns or "checkpoint_blobs.version" in missing_columns:
                raise ValueError(
                    "Unsupported Postgres checkpoint schema. "
                    "LGMI currently targets full PostgresSaver history tables, not ShallowPostgresSaver."
                )
            raise ValueError(f"Missing LangGraph Postgres checkpoint column(s): {names}")

    def _columns(self, cur: Any, table_name: str) -> set[str]:
        cur.execute(
            """
            select column_name
            from information_schema.columns
            where table_schema = %s and table_name = %s
            """,
            (self.schema, table_name),
        )
        return {row["column_name"] for row in cur.fetchall()}

    def _has_column(self, cur: Any, table_name: str, column_name: str) -> bool:
        return column_name in self._columns(cur, table_name)

    def _table_count(self, cur: Any, table_name: str) -> int:
        cur.execute(self._sql("select count(*) as count from {" + table_name + "}"))
        return int(cur.fetchone()["count"])

    def _latest_migration_version(self, cur: Any) -> int | None:
        if not self._columns(cur, "checkpoint_migrations"):
            return None
        cur.execute(self._sql("select max(v) as version from {checkpoint_migrations}"))
        value = cur.fetchone()["version"]
        return int(value) if value is not None else None

    def _fetch_checkpoint_row(
        self,
        cur: Any,
        thread_id: str,
        checkpoint_id: str,
        *,
        checkpoint_ns: str | None = None,
        include_checkpoint: bool,
    ) -> dict[str, Any] | None:
        namespace_sql, params = self._namespace_filter(checkpoint_ns)
        cur.execute(
            self._sql(
                f"""
                select thread_id, checkpoint_ns, checkpoint_id,
                       parent_checkpoint_id, type, checkpoint, metadata
                from {{checkpoints}}
                where thread_id = %s and checkpoint_id = %s
                {namespace_sql}
                order by checkpoint_ns
                limit 1
                """
            ),
            (thread_id, checkpoint_id, *params),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return self._checkpoint_row_to_dict(cur, row, include_checkpoint=include_checkpoint)

    def _incoming_writes_checkpoint_id(
        self,
        cur: Any,
        thread_id: str,
        checkpoint_id: str,
        checkpoint_ns: str | None,
    ) -> str:
        namespace_sql, params = self._namespace_filter(checkpoint_ns)
        cur.execute(
            self._sql(
                f"""
                select parent_checkpoint_id
                from {{checkpoints}}
                where thread_id = %s and checkpoint_id = %s
                {namespace_sql}
                order by checkpoint_ns
                limit 1
                """
            ),
            (thread_id, checkpoint_id, *params),
        )
        row = cur.fetchone()
        if row is None or not row["parent_checkpoint_id"]:
            return checkpoint_id

        parent_checkpoint_id = str(row["parent_checkpoint_id"])
        namespace_sql, params = self._namespace_filter(checkpoint_ns)
        cur.execute(
            self._sql(
                f"""
                select count(*) as count
                from {{checkpoint_writes}}
                where thread_id = %s and checkpoint_id = %s
                {namespace_sql}
                """
            ),
            (thread_id, parent_checkpoint_id, *params),
        )
        return parent_checkpoint_id if int(cur.fetchone()["count"]) else checkpoint_id

    def _thread_namespaces(self, cur: Any, thread_id: str) -> list[dict[str, Any]]:
        cur.execute(
            self._sql(
                """
                select checkpoint_ns,
                       count(*) as checkpoint_count,
                       min(checkpoint_id) as first_checkpoint_id,
                       max(checkpoint_id) as latest_checkpoint_id
                from {checkpoints}
                where thread_id = %s
                group by checkpoint_ns
                order by checkpoint_ns
                """
            ),
            (thread_id,),
        )
        return [dict(row) for row in cur.fetchall()]

    def _namespace_filter(self, checkpoint_ns: str | None) -> tuple[str, tuple[str, ...]]:
        if checkpoint_ns is None:
            return "", ()
        return "and checkpoint_ns = %s", (checkpoint_ns,)

    def _checkpoint_row_to_dict(
        self,
        cur: Any,
        row: Mapping[str, Any],
        *,
        include_checkpoint: bool,
    ) -> dict[str, Any]:
        raw_checkpoint = _dict_copy(row["checkpoint"])
        checkpoint = self._hydrate_checkpoint(cur, row, raw_checkpoint)
        metadata = _dict_copy(row["metadata"])
        checkpoint_blob = self._jsonb_blob(checkpoint)
        metadata_blob = self._jsonb_blob(metadata)
        item: dict[str, Any] = {
            "thread_id": row["thread_id"],
            "checkpoint_ns": row["checkpoint_ns"],
            "checkpoint_id": row["checkpoint_id"],
            "parent_checkpoint_id": row["parent_checkpoint_id"],
            "type": row["type"],
            "byte_size": checkpoint_blob["byte_size"],
            "metadata": metadata_blob,
            "checkpoint": checkpoint_blob if include_checkpoint else self._blob_summary(checkpoint_blob),
        }

        item["ts"] = checkpoint.get("ts")
        item["updated_channels"] = checkpoint.get("updated_channels", [])
        channel_values = checkpoint.get("channel_values")
        if isinstance(channel_values, Mapping):
            item["channel_names"] = list(channel_values.keys())

        if isinstance(metadata, Mapping):
            item["step"] = metadata.get("step")
            item["source"] = metadata.get("source")
        return item

    def _hydrate_checkpoint(
        self,
        cur: Any,
        row: Mapping[str, Any],
        checkpoint: dict[str, Any],
    ) -> dict[str, Any]:
        channel_values = _dict_copy(checkpoint.get("channel_values"))
        channel_versions = checkpoint.get("channel_versions")
        if not isinstance(channel_versions, Mapping):
            checkpoint["channel_values"] = channel_values
            return checkpoint

        channels = [str(channel) for channel in channel_versions]
        if not channels:
            checkpoint["channel_values"] = channel_values
            return checkpoint

        cur.execute(
            self._sql(
                """
                select channel, version, type, blob
                from {checkpoint_blobs}
                where thread_id = %s
                  and checkpoint_ns = %s
                  and channel = any(%s)
                """
            ),
            (row["thread_id"], row["checkpoint_ns"], channels),
        )
        for blob_row in cur.fetchall():
            channel = str(blob_row["channel"])
            if str(blob_row["version"]) != str(channel_versions.get(channel)):
                continue
            decoded = self._decode_typed_blob(blob_row["type"], blob_row["blob"])
            if decoded["decoded"]:
                channel_values[channel] = decoded["value"]
            elif channel not in channel_values or channel_values[channel] is True:
                channel_values[channel] = {
                    "_lgmi_decode_error": decoded.get("error"),
                    "preview": decoded.get("preview"),
                }

        checkpoint["channel_values"] = channel_values
        return checkpoint

    def _write_row_to_dict(self, row: Mapping[str, Any]) -> dict[str, Any]:
        value = self._decode_typed_blob(row["type"], row["blob"])
        return {
            "id": f"{row['checkpoint_id']}:{row['task_id']}:{row['idx']}",
            "thread_id": row["thread_id"],
            "checkpoint_ns": row["checkpoint_ns"],
            "checkpoint_id": row["checkpoint_id"],
            "task_id": row["task_id"],
            "task_path": row.get("task_path", ""),
            "idx": row["idx"],
            "channel": row["channel"],
            "type": row["type"],
            "byte_size": _byte_size(row["blob"]),
            "value": value,
        }

    def _decode_typed_blob(self, blob_type: str | None, blob: Any) -> dict[str, Any]:
        blob_bytes = _bytes(blob)
        if blob_bytes is None:
            return {
                "type": blob_type,
                "byte_size": 0,
                "decoded": True,
                "encoding": "null",
                "value": None,
                "preview": "",
            }

        if blob_type == "empty":
            return {
                "type": blob_type,
                "byte_size": 0,
                "decoded": True,
                "encoding": "langgraph:empty",
                "value": None,
                "preview": "",
            }

        try:
            value = self._serde.loads_typed((blob_type, blob_bytes))
            json_value = _to_jsonable(value)
            return {
                "type": blob_type,
                "byte_size": len(blob_bytes),
                "decoded": True,
                "encoding": f"langgraph:{blob_type}",
                "value": json_value,
                "preview": _preview_value(json_value),
            }
        except Exception as exc:  # noqa: BLE001 - inspection should survive bad rows.
            return {
                "type": blob_type,
                "byte_size": len(blob_bytes),
                "decoded": False,
                "encoding": None,
                "value": None,
                "preview": _preview_bytes(blob_bytes),
                "error": f"{type(exc).__name__}: {exc}",
            }

    def _jsonb_blob(self, value: Any) -> dict[str, Any]:
        json_value = _to_jsonable(value)
        byte_size = len(json.dumps(json_value, ensure_ascii=False, default=str).encode("utf-8"))
        return {
            "type": "jsonb",
            "byte_size": byte_size,
            "decoded": True,
            "encoding": "jsonb",
            "value": json_value,
            "preview": _preview_value(json_value),
        }

    @staticmethod
    def _blob_summary(blob: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": blob.get("type"),
            "byte_size": blob.get("byte_size"),
            "decoded": blob.get("decoded"),
            "encoding": blob.get("encoding"),
            "preview": blob.get("preview"),
        }

    def _sql(self, template: str):
        _, _, sql = _postgres_modules()
        return sql.SQL(template).format(
            checkpoints=sql.Identifier(self.schema, "checkpoints"),
            checkpoint_blobs=sql.Identifier(self.schema, "checkpoint_blobs"),
            checkpoint_writes=sql.Identifier(self.schema, "checkpoint_writes"),
            checkpoint_migrations=sql.Identifier(self.schema, "checkpoint_migrations"),
        )


def _postgres_modules():
    try:
        import psycopg
        from psycopg import sql
        from psycopg.rows import dict_row
    except ImportError as exc:  # pragma: no cover - exercised by users without the extra.
        raise RuntimeError(
            "Postgres inspection requires optional dependencies. "
            "Install with `uv sync --extra postgres` or `pip install 'langgraph-memory-inspector[postgres]'`."
        ) from exc
    return psycopg, dict_row, sql


def _dict_copy(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _bytes(value: Any) -> bytes | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, memoryview):
        return value.tobytes()
    return bytes(value)


def _byte_size(value: Any) -> int:
    data = _bytes(value)
    return len(data) if data is not None else 0
