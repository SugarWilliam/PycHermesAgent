"""Explicit skill context binding for the Hermes agent loop."""

from __future__ import annotations

from pathlib import Path
from typing import Final

from pyc_hermes_agent.contracts import ChatMessage
from pyc_hermes_agent.llm_gateway import load_skill_metadata

# Canonical Phase 1 skill runtime policy (sidecar listings, AgentLoop `start` payload). Deferrals: ADR.
SKILLS_RUNTIME_POLICY: Final[dict[str, str]] = {
    "activation_mode": "explicit_only",
    "script_execution": "disabled",
    "agent_loop_field": "activated_skills",
    "policy_id": "skill-runtime-permissions-phase1-v0.2.0",
    "policy_adr": "docs/design/ADR_Skill_Runtime_Permissions_Phase1_v0.2.0.md",
}

_SKILL_OPEN_TAG = "<skill-context>"
_SKILL_CLOSE_TAG = "</skill-context>"


def build_skill_context_messages(root: Path, skill_names: list[str] | None) -> list[ChatMessage]:
    requested = [name.strip() for name in skill_names or [] if name.strip()]
    if not requested:
        return []

    skills = {skill.name: skill for skill in load_skill_metadata(root)}
    messages: list[ChatMessage] = []
    for name in requested:
        metadata = skills.get(name)
        if metadata is None:
            raise ValueError(f"Unknown activated skill: {name}")
        body = _extract_skill_body(metadata.path)
        content = "\n".join(
            [
                _SKILL_OPEN_TAG,
                f"Active skill: {metadata.name}",
                f"Description: {metadata.description}",
                f"Source: {metadata.path}",
                "Runtime policy: Script execution is disabled in this phase.",
                "",
                "Instructions:",
                body,
                _SKILL_CLOSE_TAG,
            ]
        )
        messages.append(ChatMessage(role="system", content=content))
    return messages


def _extract_skill_body(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        return text.strip()
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "\n".join(lines[index + 1 :]).strip()
    return text.strip()


__all__ = ["SKILLS_RUNTIME_POLICY", "build_skill_context_messages"]
