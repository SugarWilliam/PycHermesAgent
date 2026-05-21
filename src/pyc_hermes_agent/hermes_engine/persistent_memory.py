"""Hermes-inspired file-backed long-term memory landing zone."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pyc_hermes_agent.common import ensure_runtime_directories, resolve_runtime_paths


_ENTRY_DELIMITER = "\n§\n"
_TARGET_FILE_NAMES = {
    "memory": "MEMORY.md",
    "user": "USER.md",
}
_TARGET_HEADERS = {
    "memory": "MEMORY (persistent notes)",
    "user": "USER PROFILE (persistent preferences)",
}


@dataclass(frozen=True, slots=True)
class PersistentMemorySnapshot:
    memory_entries: tuple[str, ...] = ()
    user_entries: tuple[str, ...] = ()


class PersistentMemoryStore:
    def __init__(self, root: Path | None = None) -> None:
        runtime_paths = ensure_runtime_directories(resolve_runtime_paths(root))
        self._memories_root = runtime_paths.local_data_dir / "hermes_engine" / "memories"
        self._memories_root.mkdir(parents=True, exist_ok=True)

    def resolve_path(self, target: str) -> Path:
        normalized_target = _normalize_target(target)
        return self._memories_root / _TARGET_FILE_NAMES[normalized_target]

    def load_entries(self, target: str) -> list[str]:
        path = self.resolve_path(target)
        if not path.exists():
            return []
        raw = path.read_text(encoding="utf-8")
        if not raw.strip():
            return []
        return _normalize_entries(raw.split(_ENTRY_DELIMITER))

    def save_entries(self, target: str, entries: list[str]) -> list[str]:
        normalized_entries = _normalize_entries(entries)
        path = self.resolve_path(target)
        _write_text_atomic(path, _ENTRY_DELIMITER.join(normalized_entries))
        return list(normalized_entries)

    def append(self, target: str, content: str) -> list[str]:
        normalized_content = _normalize_entry(content)
        if not normalized_content:
            raise ValueError("Memory entry is required.")

        entries = self.load_entries(target)
        if normalized_content not in entries:
            entries.append(normalized_content)
            self.save_entries(target, entries)
        return entries

    def replace(self, target: str, match_text: str, content: str) -> list[str]:
        normalized_content = _normalize_entry(content)
        if not normalized_content:
            raise ValueError("Replacement memory entry is required.")

        entries = self.load_entries(target)
        index = _find_unique_entry_index(entries, match_text)
        entries[index] = normalized_content
        return self.save_entries(target, entries)

    def remove(self, target: str, match_text: str) -> list[str]:
        entries = self.load_entries(target)
        index = _find_unique_entry_index(entries, match_text)
        entries.pop(index)
        return self.save_entries(target, entries)

    def load_snapshot(self) -> PersistentMemorySnapshot:
        return PersistentMemorySnapshot(
            memory_entries=tuple(self.load_entries("memory")),
            user_entries=tuple(self.load_entries("user")),
        )

    def format_for_system_prompt(self, target: str) -> str | None:
        normalized_target = _normalize_target(target)
        entries = self.load_entries(normalized_target)
        if not entries:
            return None
        header = _TARGET_HEADERS[normalized_target]
        return header + "\n" + _ENTRY_DELIMITER.join(entries)


def _normalize_target(target: str) -> str:
    normalized_target = target.strip().lower()
    if normalized_target not in _TARGET_FILE_NAMES:
        raise ValueError(f"Unsupported persistent memory target: {target!r}")
    return normalized_target


def _normalize_entry(content: str) -> str:
    return content.strip()


def _normalize_entries(entries: list[str]) -> list[str]:
    normalized_entries: list[str] = []
    seen_entries: set[str] = set()
    for entry in entries:
        normalized_entry = _normalize_entry(str(entry))
        if not normalized_entry or normalized_entry in seen_entries:
            continue
        seen_entries.add(normalized_entry)
        normalized_entries.append(normalized_entry)
    return normalized_entries


def _find_unique_entry_index(entries: list[str], match_text: str) -> int:
    needle = match_text.strip()
    if not needle:
        raise ValueError("Match text is required.")

    matches = [index for index, entry in enumerate(entries) if needle in entry]
    if not matches:
        raise KeyError(f"No persistent memory entry matched {needle!r}.")
    if len(matches) > 1:
        raise ValueError(f"Multiple persistent memory entries matched {needle!r}.")
    return matches[0]


def _write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(path)


__all__ = ["PersistentMemorySnapshot", "PersistentMemoryStore"]
