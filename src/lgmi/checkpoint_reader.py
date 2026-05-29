from __future__ import annotations

import datetime as dt
import json
import sqlite3
from collections.abc import Iterable, Mapping
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer


PREVIEW_BYTES = 160
PREVIEW_CHARS = 500
MAX_JSON_DEPTH = 12
MAX_SEQUENCE_ITEMS = 250


class SQLiteCheckpointReader:
    """Read LangGraph SQLite checkpoint databases without mutating them."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path).expanduser().resolve()
        self._serde = JsonPlusSerializer()

    def summary(self) -> dict[str, Any]:
        with self._connect() as conn:
            checkpoint_count = self._table_count(conn, "checkpoints")
            write_count = self._table_count(conn, "writes")
            thread_rows = conn.execute(
                """
                select thread_id,
                       count(*) as checkpoint_count,
                       min(rowid) as first_rowid,
                       max(rowid) as latest_rowid
                from checkpoints
                group by thread_id
                order by thread_id
                """
            ).fetchall()
            namespaces = [
                row["checkpoint_ns"]
                for row in conn.execute(
                    """
                    select distinct checkpoint_ns
                    from checkpoints
                    order by checkpoint_ns
                    """
                ).fetchall()
            ]
            diagnostics_count = self._diagnostics_count(conn)

        return {
            "db_path": str(self.db_path),
            "exists": self.db_path.exists(),
            "file_size_bytes": self.db_path.stat().st_size if self.db_path.exists() else 0,
            "checkpoint_count": checkpoint_count,
            "write_count": write_count,
            "thread_count": len(thread_rows),
            "diagnostics_count": diagnostics_count,
            "checkpoint_namespaces": namespaces,
            "threads": [dict(row) for row in thread_rows],
        }

    def list_threads(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                select c.thread_id,
                       count(*) as checkpoint_count,
                       min(c.rowid) as first_rowid,
                       max(c.rowid) as latest_rowid,
                       count(distinct c.checkpoint_ns) as namespace_count,
                       coalesce(w.write_count, 0) as write_count
                from checkpoints c
                left join (
                    select thread_id, count(*) as write_count
                    from writes
                    group by thread_id
                ) w on w.thread_id = c.thread_id
                group by c.thread_id
                order by max(c.rowid) desc
                """
            ).fetchall()

            threads: list[dict[str, Any]] = []
            for row in rows:
                latest = conn.execute(
                    """
                    select rowid, thread_id, checkpoint_ns, checkpoint_id,
                           parent_checkpoint_id, type, checkpoint, metadata
                    from checkpoints
                    where thread_id = ? and rowid = ?
                    """,
                    (row["thread_id"], row["latest_rowid"]),
                ).fetchone()
                item = dict(row)
                item["latest_checkpoint"] = (
                    self._checkpoint_row_to_dict(latest, include_checkpoint=False)
                    if latest
                    else None
                )
                item["checkpoint_namespaces"] = self._thread_namespaces(
                    conn, str(row["thread_id"])
                )
                threads.append(item)
            return threads

    def list_checkpoints(
        self,
        thread_id: str,
        checkpoint_ns: str | None = None,
        *,
        limit: int | None = None,
        offset: int = 0,
        diagnostic: bool | None = None,
        changed_path: str | None = None,
        checkpoint_id_prefix: str | None = None,
    ) -> list[dict[str, Any]]:
        if offset < 0:
            raise ValueError("offset must be >= 0")
        if limit is not None and limit < 1:
            raise ValueError("limit must be >= 1")
        with self._connect() as conn:
            if diagnostic is not None or changed_path:
                rows = self._filtered_checkpoint_rows(
                    conn,
                    thread_id,
                    checkpoint_ns,
                    diagnostic=diagnostic,
                    changed_path=changed_path,
                    checkpoint_id_prefix=checkpoint_id_prefix,
                )
                selected_rows = rows[offset : offset + limit if limit is not None else None]
                return [
                    self._checkpoint_row_to_dict(row, include_checkpoint=False)
                    for row in selected_rows
                ]

            namespace_sql, params = self._namespace_filter(checkpoint_ns)
            prefix_sql, prefix_params = _checkpoint_id_prefix_filter(checkpoint_id_prefix, placeholder="?")
            limit_sql = "" if limit is None else "limit ? offset ?"
            limit_params: tuple[int, ...] = () if limit is None else (limit, offset)
            rows = conn.execute(
                f"""
                select rowid, thread_id, checkpoint_ns, checkpoint_id,
                       parent_checkpoint_id, type, checkpoint, metadata
                from checkpoints
                where thread_id = ?
                {namespace_sql}
                {prefix_sql}
                order by rowid
                {limit_sql}
                """,
                (thread_id, *params, *prefix_params, *limit_params),
            ).fetchall()
            return [
                self._checkpoint_row_to_dict(row, include_checkpoint=False)
                for row in rows
            ]

    def count_checkpoints(
        self,
        thread_id: str,
        checkpoint_ns: str | None = None,
        *,
        diagnostic: bool | None = None,
        changed_path: str | None = None,
        checkpoint_id_prefix: str | None = None,
    ) -> int:
        with self._connect() as conn:
            if diagnostic is not None or changed_path:
                return len(
                    self._filtered_checkpoint_rows(
                        conn,
                        thread_id,
                        checkpoint_ns,
                        diagnostic=diagnostic,
                        changed_path=changed_path,
                        checkpoint_id_prefix=checkpoint_id_prefix,
                    )
                )

            namespace_sql, params = self._namespace_filter(checkpoint_ns)
            prefix_sql, prefix_params = _checkpoint_id_prefix_filter(checkpoint_id_prefix, placeholder="?")
            return int(
                conn.execute(
                    f"""
                    select count(*)
                    from checkpoints
                    where thread_id = ?
                    {namespace_sql}
                    {prefix_sql}
                    """,
                    (thread_id, *params, *prefix_params),
                ).fetchone()[0]
            )

    def get_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str,
        checkpoint_ns: str | None = None,
    ) -> dict[str, Any] | None:
        with self._connect() as conn:
            namespace_sql, params = self._namespace_filter(checkpoint_ns)
            row = conn.execute(
                f"""
                select rowid, thread_id, checkpoint_ns, checkpoint_id,
                       parent_checkpoint_id, type, checkpoint, metadata
                from checkpoints
                where thread_id = ? and checkpoint_id = ?
                {namespace_sql}
                order by rowid
                limit 1
                """,
                (thread_id, checkpoint_id, *params),
            ).fetchone()
            if not row:
                return None
            return self._checkpoint_row_to_dict(row, include_checkpoint=True)

    def list_writes(
        self,
        thread_id: str,
        checkpoint_id: str,
        checkpoint_ns: str | None = None,
    ) -> list[dict[str, Any]]:
        with self._connect() as conn:
            writes_checkpoint_id = self._incoming_writes_checkpoint_id(
                conn, thread_id, checkpoint_id, checkpoint_ns
            )
            namespace_sql, params = self._namespace_filter(checkpoint_ns)
            rows = conn.execute(
                f"""
                select rowid, thread_id, checkpoint_ns, checkpoint_id,
                       task_id, idx, channel, type, value
                from writes
                where thread_id = ? and checkpoint_id = ?
                {namespace_sql}
                order by task_id, idx, rowid
                """,
                (thread_id, writes_checkpoint_id, *params),
            ).fetchall()
            return [self._write_row_to_dict(row) for row in rows]

    def _incoming_writes_checkpoint_id(
        self,
        conn: sqlite3.Connection,
        thread_id: str,
        checkpoint_id: str,
        checkpoint_ns: str | None,
    ) -> str:
        namespace_sql, params = self._namespace_filter(checkpoint_ns)
        row = conn.execute(
            f"""
            select parent_checkpoint_id
            from checkpoints
            where thread_id = ? and checkpoint_id = ?
            {namespace_sql}
            order by rowid
            limit 1
            """,
            (thread_id, checkpoint_id, *params),
        ).fetchone()
        if not row or not row["parent_checkpoint_id"]:
            return checkpoint_id

        parent_checkpoint_id = str(row["parent_checkpoint_id"])
        namespace_sql, params = self._namespace_filter(checkpoint_ns)
        parent_write_count = conn.execute(
            f"""
            select count(*)
            from writes
            where thread_id = ? and checkpoint_id = ?
            {namespace_sql}
            """,
            (thread_id, parent_checkpoint_id, *params),
        ).fetchone()[0]
        return parent_checkpoint_id if parent_write_count else checkpoint_id

    def _thread_namespaces(
        self, conn: sqlite3.Connection, thread_id: str
    ) -> list[dict[str, Any]]:
        rows = conn.execute(
            """
            select checkpoint_ns,
                   count(*) as checkpoint_count,
                   min(rowid) as first_rowid,
                   max(rowid) as latest_rowid
            from checkpoints
            where thread_id = ?
            group by checkpoint_ns
            order by checkpoint_ns
            """,
            (thread_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def _filtered_checkpoint_rows(
        self,
        conn: sqlite3.Connection,
        thread_id: str,
        checkpoint_ns: str | None,
        *,
        diagnostic: bool | None,
        changed_path: str | None,
        checkpoint_id_prefix: str | None,
    ) -> list[sqlite3.Row]:
        namespace_sql, params = self._namespace_filter(checkpoint_ns)
        prefix_sql, prefix_params = _checkpoint_id_prefix_filter(checkpoint_id_prefix, placeholder="?")
        rows = conn.execute(
            f"""
            select rowid, thread_id, checkpoint_ns, checkpoint_id,
                   parent_checkpoint_id, type, checkpoint, metadata
            from checkpoints
            where thread_id = ?
            {namespace_sql}
            {prefix_sql}
            order by rowid
            """,
            (thread_id, *params, *prefix_params),
        ).fetchall()
        channel = _channel_from_state_path(changed_path)
        return [
            row
            for row in rows
            if self._checkpoint_row_matches(row, diagnostic=diagnostic, changed_channel=channel)
        ]

    def _checkpoint_row_matches(
        self,
        row: sqlite3.Row,
        *,
        diagnostic: bool | None,
        changed_channel: str | None,
    ) -> bool:
        checkpoint = self._decode_blob(row["type"], row["checkpoint"])
        value = checkpoint.get("value") if checkpoint.get("decoded") else None
        if not isinstance(value, Mapping):
            return diagnostic is not True and changed_channel is None
        channel_values = value.get("channel_values")
        diagnostics = []
        if isinstance(channel_values, Mapping):
            raw_diagnostics = channel_values.get("diagnostics")
            diagnostics = raw_diagnostics if isinstance(raw_diagnostics, list) else []

        if diagnostic is True and not diagnostics:
            return False
        if diagnostic is False and diagnostics:
            return False
        if changed_channel:
            updated_channels = value.get("updated_channels")
            if not isinstance(updated_channels, list) or changed_channel not in updated_channels:
                return False
        return True

    def _namespace_filter(self, checkpoint_ns: str | None) -> tuple[str, tuple[str, ...]]:
        if checkpoint_ns is None:
            return "", ()
        return "and checkpoint_ns = ?", (checkpoint_ns,)

    def _connect(self) -> sqlite3.Connection:
        if not self.db_path.exists():
            raise FileNotFoundError(f"Checkpoint database not found: {self.db_path}")

        conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        self._ensure_schema(conn)
        return conn

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        table_names = {
            row["name"]
            for row in conn.execute(
                "select name from sqlite_master where type = 'table'"
            ).fetchall()
        }
        missing = {"checkpoints", "writes"} - table_names
        if missing:
            names = ", ".join(sorted(missing))
            raise ValueError(f"Missing LangGraph checkpoint table(s): {names}")

    def _table_count(self, conn: sqlite3.Connection, table_name: str) -> int:
        return int(conn.execute(f"select count(*) from {table_name}").fetchone()[0])

    def _diagnostics_count(self, conn: sqlite3.Connection) -> int:
        count = 0
        rows = conn.execute("select type, checkpoint from checkpoints").fetchall()
        for row in rows:
            checkpoint = self._decode_blob(row["type"], row["checkpoint"])
            value = checkpoint.get("value")
            if not isinstance(value, Mapping):
                continue
            channel_values = value.get("channel_values")
            if not isinstance(channel_values, Mapping):
                continue
            diagnostics = channel_values.get("diagnostics")
            if isinstance(diagnostics, list):
                count += len(diagnostics)
        return count

    def _checkpoint_row_to_dict(
        self, row: sqlite3.Row, *, include_checkpoint: bool
    ) -> dict[str, Any]:
        metadata = self._decode_blob(None, row["metadata"], prefer_json=True)
        checkpoint = self._decode_blob(row["type"], row["checkpoint"])
        item: dict[str, Any] = {
            "rowid": row["rowid"],
            "thread_id": row["thread_id"],
            "checkpoint_ns": row["checkpoint_ns"],
            "checkpoint_id": row["checkpoint_id"],
            "parent_checkpoint_id": row["parent_checkpoint_id"],
            "type": row["type"],
            "byte_size": len(row["checkpoint"]) if row["checkpoint"] else 0,
            "metadata": metadata,
            "checkpoint": checkpoint if include_checkpoint else self._blob_summary(checkpoint),
        }

        if checkpoint.get("decoded") and isinstance(checkpoint.get("value"), Mapping):
            value = checkpoint["value"]
            item["ts"] = value.get("ts")
            item["updated_channels"] = value.get("updated_channels", [])
            channel_values = value.get("channel_values")
            if isinstance(channel_values, Mapping):
                item["channel_names"] = list(channel_values.keys())

        if metadata.get("decoded") and isinstance(metadata.get("value"), Mapping):
            item["step"] = metadata["value"].get("step")
            item["source"] = metadata["value"].get("source")

        return item

    def _write_row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        value = self._decode_blob(row["type"], row["value"])
        return {
            "rowid": row["rowid"],
            "thread_id": row["thread_id"],
            "checkpoint_ns": row["checkpoint_ns"],
            "checkpoint_id": row["checkpoint_id"],
            "task_id": row["task_id"],
            "idx": row["idx"],
            "channel": row["channel"],
            "type": row["type"],
            "byte_size": len(row["value"]) if row["value"] else 0,
            "value": value,
        }

    def _decode_blob(
        self, blob_type: str | None, blob: bytes | None, *, prefer_json: bool = False
    ) -> dict[str, Any]:
        if blob is None:
            return {
                "type": blob_type,
                "byte_size": 0,
                "decoded": True,
                "encoding": "null",
                "value": None,
                "preview": "",
            }

        attempts: list[tuple[str, Any]] = []
        if prefer_json or _looks_like_json(blob):
            attempts.append(("json", None))
        if blob_type:
            attempts.append((f"langgraph:{blob_type}", blob_type))
        if not prefer_json and not _looks_like_json(blob):
            attempts.append(("json", None))
        attempts.append(("utf-8", None))

        errors: list[str] = []
        for encoding, typed in attempts:
            try:
                if encoding == "json":
                    value = json.loads(blob.decode("utf-8"))
                elif encoding == "utf-8":
                    value = blob.decode("utf-8")
                else:
                    value = self._serde.loads_typed((typed, blob))
                json_value = _to_jsonable(value)
                return {
                    "type": blob_type,
                    "byte_size": len(blob),
                    "decoded": True,
                    "encoding": encoding,
                    "value": json_value,
                    "preview": _preview_value(json_value),
                }
            except Exception as exc:  # noqa: BLE001 - decoding must never kill inspection.
                errors.append(f"{encoding}: {type(exc).__name__}: {exc}")

        return {
            "type": blob_type,
            "byte_size": len(blob),
            "decoded": False,
            "encoding": None,
            "value": None,
            "preview": _preview_bytes(blob),
            "error": errors[-1] if errors else "Unable to decode blob",
            "attempts": errors,
        }

    def _blob_summary(self, blob: dict[str, Any]) -> dict[str, Any]:
        summary = {
            "type": blob.get("type"),
            "byte_size": blob.get("byte_size"),
            "decoded": blob.get("decoded"),
            "encoding": blob.get("encoding"),
            "preview": blob.get("preview"),
        }
        if not blob.get("decoded"):
            summary["error"] = blob.get("error")
        return summary


def _looks_like_json(blob: bytes) -> bool:
    stripped = blob.lstrip()
    return stripped.startswith((b"{", b"[", b'"', b"true", b"false", b"null"))


def _preview_bytes(blob: bytes) -> str:
    sample = blob[:PREVIEW_BYTES]
    text = sample.decode("utf-8", errors="replace")
    hex_preview = sample.hex()
    if len(hex_preview) > PREVIEW_CHARS:
        hex_preview = f"{hex_preview[:PREVIEW_CHARS]}..."
    if len(text) > PREVIEW_CHARS:
        text = f"{text[:PREVIEW_CHARS]}..."
    return f"text={text!r} hex={hex_preview}"


def _preview_value(value: Any) -> str:
    try:
        rendered = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    except TypeError:
        rendered = repr(value)
    if len(rendered) > PREVIEW_CHARS:
        return f"{rendered[:PREVIEW_CHARS]}..."
    return rendered


def _channel_from_state_path(path: str | None) -> str | None:
    if not path:
        return None
    cleaned = path.strip().strip(".")
    if not cleaned:
        return None
    if cleaned.startswith("state."):
        cleaned = cleaned.removeprefix("state.")
    return cleaned.split(".", 1)[0].split("[", 1)[0] or None


def _checkpoint_id_prefix_filter(
    checkpoint_id_prefix: str | None,
    *,
    placeholder: str,
) -> tuple[str, tuple[str, ...]]:
    prefix = (checkpoint_id_prefix or "").strip()
    if not prefix:
        return "", ()
    return f"and checkpoint_id like {placeholder} escape '\\'", (f"{_escape_like(prefix)}%",)


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _to_jsonable(
    value: Any,
    *,
    depth: int = 0,
    seen: set[int] | None = None,
) -> Any:
    if seen is None:
        seen = set()

    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, bytes):
        return {
            "_type": "bytes",
            "byte_size": len(value),
            "preview": _preview_bytes(value),
        }
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (dt.datetime, dt.date, dt.time)):
        return value.isoformat()
    if depth >= MAX_JSON_DEPTH:
        return repr(value)

    value_id = id(value)
    if value_id in seen:
        return {"_type": type(value).__name__, "repr": "<recursive>"}
    seen.add(value_id)

    try:
        if isinstance(value, Mapping):
            return {
                str(key): _to_jsonable(item, depth=depth + 1, seen=seen)
                for key, item in value.items()
            }
        if isinstance(value, Iterable) and not isinstance(value, str | bytes):
            items = list(value)
            rendered = [
                _to_jsonable(item, depth=depth + 1, seen=seen)
                for item in items[:MAX_SEQUENCE_ITEMS]
            ]
            if len(items) > MAX_SEQUENCE_ITEMS:
                rendered.append(
                    {
                        "_truncated": True,
                        "remaining_items": len(items) - MAX_SEQUENCE_ITEMS,
                    }
                )
            return rendered
        if hasattr(value, "model_dump"):
            dumped = value.model_dump(mode="json")
            if isinstance(dumped, Mapping):
                dumped = dict(dumped)
                dumped.setdefault("_type", f"{type(value).__module__}.{type(value).__name__}")
            return _to_jsonable(dumped, depth=depth + 1, seen=seen)
        if is_dataclass(value) and not isinstance(value, type):
            return _to_jsonable(asdict(value), depth=depth + 1, seen=seen)
        if hasattr(value, "dict"):
            return _to_jsonable(value.dict(), depth=depth + 1, seen=seen)
        return repr(value)
    finally:
        seen.discard(value_id)
