from __future__ import annotations

from typing import Any, Protocol


class CheckpointReader(Protocol):
    """Read-only checkpoint store contract used by the inspector API."""

    def summary(self) -> dict[str, Any]:
        """Return store-level counts, namespaces, and adapter metadata."""

    def list_threads(self) -> list[dict[str, Any]]:
        """Return checkpoint threads ordered for debugging."""

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
        """Return timeline checkpoints for a thread."""

    def count_checkpoints(
        self,
        thread_id: str,
        checkpoint_ns: str | None = None,
        *,
        diagnostic: bool | None = None,
        changed_path: str | None = None,
        checkpoint_id_prefix: str | None = None,
    ) -> int:
        """Return checkpoint count for a thread and optional timeline filters."""

    def get_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str,
        checkpoint_ns: str | None = None,
    ) -> dict[str, Any] | None:
        """Return one decoded checkpoint snapshot."""

    def list_writes(
        self,
        thread_id: str,
        checkpoint_id: str,
        checkpoint_ns: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return writes that produced the selected checkpoint snapshot."""
