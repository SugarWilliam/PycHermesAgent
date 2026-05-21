"""Single-process ownership guard for MRAG JSON persistence."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


MRAG_LOCK_FILE = "mrag.owner.lock"


class MRAGStorageLockedError(RuntimeError):
    """Raised when a persisted MRAG storage root is owned elsewhere."""

    def __init__(self, storage_root: Path, lock_path: Path, owner_details: dict | None = None) -> None:
        self.storage_root = storage_root
        self.lock_path = lock_path
        self.owner_details = owner_details or {}
        super().__init__(f"MRAG storage root is locked by another owner: {storage_root}")


@dataclass
class _OwnerState:
    owner_id: str
    ref_count: int
    lock_path: Path


_PROCESS_OWNERS: dict[Path, _OwnerState] = {}


class MRAGStorageOwner:
    """Reference-counted process-local handle for a storage root lock."""

    def __init__(self, storage_root: Path, state: _OwnerState) -> None:
        self.storage_root = storage_root
        self._state = state
        self._closed = False

    @property
    def lock_path(self) -> Path:
        return self._state.lock_path

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        state = _PROCESS_OWNERS.get(self.storage_root)
        if state is None:
            return
        state.ref_count -= 1
        if state.ref_count > 0:
            return
        _PROCESS_OWNERS.pop(self.storage_root, None)
        _remove_lock_if_owned(state.lock_path, state.owner_id)


def acquire_mrag_storage_owner(storage_root: Path) -> MRAGStorageOwner:
    resolved_root = storage_root.resolve()
    lock_path = resolved_root / MRAG_LOCK_FILE
    existing = _PROCESS_OWNERS.get(resolved_root)
    if existing is not None:
        existing.ref_count += 1
        return MRAGStorageOwner(resolved_root, existing)

    resolved_root.mkdir(parents=True, exist_ok=True)
    owner_id = str(uuid4())
    payload = {
        "owner_id": owner_id,
        "pid": os.getpid(),
    }
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        fd = os.open(lock_path, flags, 0o644)
    except FileExistsError as exc:
        raise MRAGStorageLockedError(resolved_root, lock_path, _read_lock_payload(lock_path)) from exc
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2)

    state = _OwnerState(owner_id=owner_id, ref_count=1, lock_path=lock_path)
    _PROCESS_OWNERS[resolved_root] = state
    return MRAGStorageOwner(resolved_root, state)


def _read_lock_payload(lock_path: Path) -> dict:
    try:
        payload = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _remove_lock_if_owned(lock_path: Path, owner_id: str) -> None:
    payload = _read_lock_payload(lock_path)
    if payload.get("owner_id") != owner_id:
        return
    try:
        lock_path.unlink()
    except FileNotFoundError:
        return


__all__ = [
    "MRAG_LOCK_FILE",
    "MRAGStorageLockedError",
    "MRAGStorageOwner",
    "acquire_mrag_storage_owner",
]
