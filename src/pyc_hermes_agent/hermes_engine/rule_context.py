"""Assemble deterministic project/user rule context for AgentLoop prompts."""

from __future__ import annotations

from pathlib import Path

from pyc_hermes_agent.contracts import ChatMessage
from pyc_hermes_agent.llm_gateway.rules import discover_ordered_rule_documents

_RULE_OPEN_TAG = "<rules-context>"
_RULE_CLOSE_TAG = "</rules-context>"
_SYSTEM_STUB = (
    "[Product runtime reminder] Respect PycHermesAgent boundaries from AGENTS.md: "
    "formal MetaFramework invocation path, MRAG purity, immutable install dirs, LLM-gateway-only providers."
)


def build_rule_context_messages(root: Path) -> tuple[list[ChatMessage], list[Path]]:
    """
    Ordered policy: farthest ancestor first, workspace ``AGENTS.md`` last (later text wins socially for LLMs).

    Returns ``(messages, rule_paths_loaded)``.
    """
    paths = discover_ordered_rule_documents(root)
    bodies: list[str] = []

    bodies.append(_SYSTEM_STUB)
    for doc in paths:
        try:
            bodies.append(doc.read_text(encoding="utf-8").strip())
        except OSError:
            continue

    if len(bodies) <= 1 and not paths:
        return [], []

    merged = "\n\n---\n\n".join(chunk for chunk in bodies if chunk.strip())
    if not merged.strip():
        return [], paths

    content = "\n".join(
        [
            _RULE_OPEN_TAG,
            "Active rules (ordered: system stub, then repository chain outer → inner):",
            "",
            merged,
            _RULE_CLOSE_TAG,
        ]
    )
    return [ChatMessage(role="system", content=content)], paths


__all__ = ["build_rule_context_messages"]
