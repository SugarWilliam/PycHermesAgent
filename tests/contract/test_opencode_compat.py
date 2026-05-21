from pathlib import Path

from pyc_hermes_agent.llm_gateway import (
    discover_rule_files,
    discover_skills,
    load_opencode_like_config,
    load_skill_metadata,
)


def test_project_config_is_discoverable() -> None:
    root = Path(__file__).resolve().parents[2]
    config = load_opencode_like_config(root)
    assert config is not None
    assert "instructions" in config


def test_agents_md_is_discoverable() -> None:
    root = Path(__file__).resolve().parents[2]
    rules = discover_rule_files(root)
    assert rules
    assert rules[0].name == "AGENTS.md"


def test_project_skills_are_discoverable() -> None:
    root = Path(__file__).resolve().parents[2]
    skills = discover_skills(root)
    assert skills
    assert any(path.name == "SKILL.md" for path in skills)


def test_project_skill_metadata_is_loadable() -> None:
    root = Path(__file__).resolve().parents[2]
    metadata = load_skill_metadata(root)
    assert metadata
    assert any(skill.name == "meta-harness-governance" for skill in metadata)
