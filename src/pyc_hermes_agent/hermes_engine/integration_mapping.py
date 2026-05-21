"""Frozen Hermes mixed-integration mapping for product development."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class HermesCapabilityMapping:
    capability_id: str
    target_owner: str
    integration_mode: str
    status: str
    milestone: str
    target_module: str
    upstream_paths: tuple[str, ...] = ()
    rationale: str = ""
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class HermesMixedIntegrationPlan:
    strategy: str = "mixed"
    summary: str = ""
    mappings: tuple[HermesCapabilityMapping, ...] = field(default_factory=tuple)


_DEFAULT_PLAN = HermesMixedIntegrationPlan(
    summary=(
        "Deeply bridge Hermes session and memory data-layer concepts, rebuild the Agent runtime in "
        "hermes_engine, and keep broad gateway, browser, and CLI ecosystems outside the product core."
    ),
    mappings=(
        HermesCapabilityMapping(
            capability_id="hermes.sessions.store",
            target_owner="hermes_engine",
            integration_mode="deep-bridge",
            status="partial",
            milestone="M1",
            target_module="hermes_engine.session_store",
            upstream_paths=("hermes_state.py",),
            rationale="Hermes session persistence and resume semantics are central to long-running Agent memory.",
            notes=("Keep product ownership in hermes_engine.",),
        ),
        HermesCapabilityMapping(
            capability_id="hermes.sessions.search",
            target_owner="hermes_engine",
            integration_mode="deep-bridge",
            status="planned",
            milestone="M2",
            target_module="hermes_engine.session_recall",
            upstream_paths=("hermes_state.py", "tools/session_search_tool.py"),
            rationale="Cross-session recall should be explicit and queryable, not only raw history replay.",
        ),
        HermesCapabilityMapping(
            capability_id="hermes.memory.session-context",
            target_owner="hermes_engine",
            integration_mode="deep-bridge",
            status="implemented",
            milestone="M1",
            target_module="hermes_engine.session_context",
            upstream_paths=("gateway/session_context.py",),
            rationale="Session-scoped context isolation is a low-coupling building block for future memory and tool integrations.",
        ),
        HermesCapabilityMapping(
            capability_id="hermes.memory.prompt-injection",
            target_owner="hermes_engine",
            integration_mode="rebuild",
            status="implemented",
            milestone="M1",
            target_module="hermes_engine.memory_injection",
            upstream_paths=("agent/memory_manager.py", "agent/memory_provider.py"),
            rationale="Prompt assembly must stay under Pyc orchestration ownership while preserving memory-safety behavior.",
        ),
        HermesCapabilityMapping(
            capability_id="hermes.memory.long-term-files",
            target_owner="hermes_engine",
            integration_mode="deep-bridge",
            status="planned",
            milestone="M1",
            target_module="hermes_engine.persistent_memory",
            upstream_paths=("tools/memory_tool.py",),
            rationale="Hermes-style USER and workspace memory files directly support learned preferences and durable context.",
        ),
        HermesCapabilityMapping(
            capability_id="hermes.memory.provider-abstraction",
            target_owner="hermes_engine",
            integration_mode="deep-bridge",
            status="planned",
            milestone="M2",
            target_module="hermes_engine.memory_providers",
            upstream_paths=("agent/memory_provider.py", "agent/memory_manager.py"),
            rationale="External memory providers should be adopted as an interface seam, not as an upstream runtime transplant.",
        ),
        HermesCapabilityMapping(
            capability_id="hermes.orchestration.loop",
            target_owner="hermes_engine",
            integration_mode="rebuild",
            status="implemented",
            milestone="M1",
            target_module="hermes_engine.agent_loop",
            upstream_paths=("run_agent.py",),
            rationale="Embedding upstream run_agent.py would break the current product layer boundaries.",
            notes=("Do not embed run_agent.py as the product runtime.",),
        ),
        HermesCapabilityMapping(
            capability_id="hermes.tools.runtime",
            target_owner="hermes_engine",
            integration_mode="rebuild",
            status="partial",
            milestone="M2",
            target_module="hermes_engine.tool_registry",
            upstream_paths=("model_tools.py", "tools/registry.py", "toolsets.py"),
            rationale="Tool execution should converge on stable Pyc contracts rather than import-time upstream side effects.",
        ),
        HermesCapabilityMapping(
            capability_id="hermes.skills.discovery",
            target_owner="llm_gateway",
            integration_mode="compatibility-only",
            status="implemented",
            milestone="M2",
            target_module="llm_gateway.skills",
            upstream_paths=("tools/skills_tool.py", "agent/skill_utils.py"),
            rationale="Skill discovery semantics matter for compatibility even before full runtime activation exists.",
        ),
        HermesCapabilityMapping(
            capability_id="hermes.skills.runtime",
            target_owner="llm_gateway",
            integration_mode="rebuild",
            status="planned",
            milestone="M2",
            target_module="llm_gateway.instruction_loader",
            upstream_paths=("agent/skill_commands.py", "tools/skills_tool.py"),
            rationale="Skills should be normalized into explicit instruction bundles before the Agent runtime consumes them.",
        ),
        HermesCapabilityMapping(
            capability_id="hermes.project.rules",
            target_owner="llm_gateway",
            integration_mode="compatibility-only",
            status="partial",
            milestone="M2",
            target_module="llm_gateway.rules",
            upstream_paths=("agent/prompt_builder.py", "agent/subdirectory_hints.py"),
            rationale="Rule discovery exists today, but prompt-safe runtime loading still belongs to llm_gateway normalization.",
        ),
        HermesCapabilityMapping(
            capability_id="hermes.gateway.platforms",
            target_owner="external",
            integration_mode="subprocess-readonly",
            status="deferred",
            milestone="defer",
            target_module="",
            upstream_paths=("gateway/", "hermes_cli/", "tui_gateway/"),
            rationale="Messaging and gateway ecosystems are useful compatibility surfaces but not the first product-defining runtime core.",
        ),
        HermesCapabilityMapping(
            capability_id="hermes.browser.mcp",
            target_owner="external",
            integration_mode="subprocess-readonly",
            status="deferred",
            milestone="defer",
            target_module="",
            upstream_paths=("tools/browser_tool.py", "tools/mcp_tool.py"),
            rationale="Browser and MCP runtimes should remain outside the product core until intentionally productized.",
        ),
        HermesCapabilityMapping(
            capability_id="hermes.delegation.runtime",
            target_owner="hermes_engine",
            integration_mode="defer",
            status="deferred",
            milestone="defer",
            target_module="hermes_engine.delegation",
            upstream_paths=("tools/delegate_tool.py",),
            rationale="Delegation is valuable but should not outrun session, memory, and Copilot core work.",
        ),
    ),
)


def get_mixed_integration_plan() -> HermesMixedIntegrationPlan:
    return _DEFAULT_PLAN


def find_capability_mapping(capability_id: str) -> HermesCapabilityMapping | None:
    normalized = capability_id.strip()
    if not normalized:
        return None
    for mapping in _DEFAULT_PLAN.mappings:
        if mapping.capability_id == normalized:
            return mapping
    return None


__all__ = ["HermesCapabilityMapping", "HermesMixedIntegrationPlan", "find_capability_mapping", "get_mixed_integration_plan"]
