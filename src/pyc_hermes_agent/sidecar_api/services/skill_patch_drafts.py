"""Skill patch drafts — filesystem-backed, human-in-the-loop; never silently merged."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from pyc_hermes_agent.common import ensure_runtime_directories, resolve_runtime_paths
from pyc_hermes_agent.contracts.schemas import utc_now_iso
from pyc_hermes_agent.hermes_engine.session_store import AgentSessionStore

_DRAFT_ID_PATTERN = re.compile(r"^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$")


@dataclass(slots=True)
class SkillPatchDraft:
    draft_id: str
    created_at: str
    title: str
    body: str
    session_id: str
    source: str


def _drafts_directory(root: Path | None) -> Path:
    base = Path(root) if root is not None else Path(".")
    paths = ensure_runtime_directories(resolve_runtime_paths(base))
    directory = paths.local_data_dir / "hermes_engine" / "skill_patch_drafts"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _draft_from_dict(data: dict[str, Any]) -> SkillPatchDraft:
    return SkillPatchDraft(
        draft_id=str(data["draft_id"]),
        created_at=str(data.get("created_at", "")),
        title=str(data.get("title", "")),
        body=str(data.get("body", "")),
        session_id=str(data.get("session_id", "")),
        source=str(data.get("source", "manual")),
    )


def list_skill_patch_drafts(root: Path | None = None) -> dict[str, Any]:
    records: list[SkillPatchDraft] = []
    for path in sorted(_drafts_directory(root).glob("*.json"), key=lambda item: item.stat().st_mtime_ns, reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                continue
            records.append(_draft_from_dict(data))
        except (OSError, json.JSONDecodeError, KeyError, TypeError):
            continue
    return {"items": [asdict(item) for item in records]}


def create_skill_patch_draft(
    root: Path | None,
    *,
    title: str,
    body: str,
    session_id: str = "",
    source: str = "manual",
) -> dict[str, Any]:
    trimmed_title = title.strip()
    draft = SkillPatchDraft(
        draft_id=str(uuid4()),
        created_at=utc_now_iso(),
        title=(trimmed_title[:240] if trimmed_title else "Untitled draft"),
        body=body,
        session_id=session_id.strip()[:256],
        source=(source.strip()[:64] or "manual"),
    )
    path = _drafts_directory(root) / f"{draft.draft_id}.json"
    path.write_text(json.dumps(asdict(draft), indent=2, ensure_ascii=True), encoding="utf-8")
    return asdict(draft)


def delete_skill_patch_draft(root: Path | None, draft_id: str) -> bool:
    normalized = draft_id.strip()
    if not _DRAFT_ID_PATTERN.fullmatch(normalized):
        return False
    path = _drafts_directory(root) / f"{normalized}.json"
    if not path.is_file():
        return False
    path.unlink()
    return True


def suggest_skill_patch_draft_from_session(root: Path | None, session_id: str) -> dict[str, Any]:
    sid = session_id.strip()
    if not sid:
        raise ValueError("Field 'session_id' is required.")

    store = AgentSessionStore(root=(Path(root).resolve() if root is not None else None))
    record = store.load(sid)
    if record is None:
        raise ValueError("Unknown session_id.")

    excerpt = ""
    for message in reversed(record.messages):
        if message.role != "assistant":
            continue
        content = (message.content or "").strip()
        if not content:
            continue
        excerpt = content[:8000]
        break
    if not excerpt:
        raise ValueError("No assistant excerpt available for suggestion.")

    title = f"Session draft ({sid[:16]})"

    prelude = """# Skill patch draft (weak automation)

> Human review required — never merged silently.
> Heuristic source: latest non-empty assistant message in session `{session}`.

## Proposed carry-over notes

```markdown
"""

    finale = """
```

## Checklist before promotion

- [ ] Verified against repository rules and `.opencode` skill layout
- [ ] Manually promoted if accepted

"""

    body = prelude.format(session=sid) + excerpt + finale
    return create_skill_patch_draft(
        root,
        title=title,
        body=body,
        session_id=sid,
        source="session_suggest",
    )


__all__ = [
    "SkillPatchDraft",
    "create_skill_patch_draft",
    "delete_skill_patch_draft",
    "list_skill_patch_drafts",
    "suggest_skill_patch_draft_from_session",
]
