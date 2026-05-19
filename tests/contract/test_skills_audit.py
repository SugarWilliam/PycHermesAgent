"""Contract tests for SkillAuditor."""

from __future__ import annotations

from pathlib import Path


from pyc_hermes_agent.hermes_engine.skills.audit import SkillAuditor


def test_auditor_records_activation() -> None:
    auditor = SkillAuditor()
    auditor.record_activation("skill-a", session_id="s1")
    entries = auditor.get_recent_entries()
    assert len(entries) == 1
    assert entries[0].skill_id == "skill-a"
    assert entries[0].action == "activated"
    assert entries[0].session_id == "s1"
    assert entries[0].timestamp != ""


def test_auditor_usage_counts() -> None:
    auditor = SkillAuditor()
    auditor.record_usage("skill-x")
    auditor.record_usage("skill-x")
    auditor.record_usage("skill-x")
    counts = auditor.get_usage_counts()
    assert counts["skill-x"] == 3


def test_auditor_save_load_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "audit.json"
    auditor = SkillAuditor(storage_path=path)
    auditor.record_activation("s1")
    auditor.record_usage("s1")
    auditor.record_usage("s1")
    auditor.save()

    auditor2 = SkillAuditor(storage_path=path)
    auditor2.load()
    assert len(auditor2.get_recent_entries()) == 3
    assert auditor2.get_usage_counts()["s1"] == 2


def test_auditor_recent_entries_limit() -> None:
    auditor = SkillAuditor()
    for i in range(100):
        auditor.record_usage(f"skill-{i}")
    recent = auditor.get_recent_entries(limit=10)
    assert len(recent) == 10
    # Should be the last 10
    assert recent[0].skill_id == "skill-90"
    assert recent[-1].skill_id == "skill-99"
