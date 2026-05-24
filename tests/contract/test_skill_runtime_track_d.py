"""Track D skill priority + overlap_group audit hints."""

from __future__ import annotations

from pathlib import Path


def _write_skill(root: Path, folder: str, *, name: str, priority: int, overlap_group: str | None) -> None:
    og_line = f"overlap_group: {overlap_group}" if overlap_group else ""
    body = "---\n"
    body += f"name: {name}\n"
    body += f"description: Desc {name}\n"
    body += f"priority: {priority}\n"
    if og_line:
        body += og_line + "\n"
    body += "---\n"
    body += f"# {name}\n"
    skill_dir = root / ".opencode" / "skills" / folder
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(body, encoding="utf-8")


def test_sort_skill_names_for_context_orders_by_priority(tmp_path: Path) -> None:
    from pyc_hermes_agent.llm_gateway.skill_runtime_audit import sort_skill_names_for_context

    _write_skill(tmp_path, "low", name="low-skill", priority=1, overlap_group=None)
    _write_skill(tmp_path, "high", name="high-skill", priority=99, overlap_group=None)

    ordered = sort_skill_names_for_context(tmp_path, ["low-skill", "high-skill"])
    assert ordered == ["high-skill", "low-skill"]


def test_overlap_group_multi_activate_surfaces_hint(tmp_path: Path) -> None:
    from pyc_hermes_agent.llm_gateway.skill_runtime_audit import collect_skill_audit_hints

    _write_skill(tmp_path, "a", name="skill-a", priority=5, overlap_group="ipc-review")
    _write_skill(tmp_path, "b", name="skill-b", priority=5, overlap_group="ipc-review")

    audit = collect_skill_audit_hints(tmp_path, ["skill-a", "skill-b"])

    hints = audit.get("overlap_group_hints") or []
    assert any(h.get("kind") == "overlap_group_multi_activate" for h in hints)
