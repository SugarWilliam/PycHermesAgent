"""Hermes orchestration seam for PycHermesAgent."""

from .agent_loop import AgentLoop, AgentLoopResult, LLMExecutor, create_meta_harness_tool_registry
from .integration_mapping import HermesCapabilityMapping, HermesMixedIntegrationPlan, find_capability_mapping, get_mixed_integration_plan
from .memory_injection import build_memory_message, build_prompt_messages
from .persistent_memory import PersistentMemorySnapshot, PersistentMemoryStore
from .planner import build_agent_plan, build_plan_message
from .runtime import (
    HermesFacade,
    get_capability_snapshot,
    get_memory_snapshot,
    get_sessions_snapshot,
    get_skills_snapshot,
    get_tools_snapshot,
)
from .session_context import bind_session_context, get_current_session_id
from .session_recall import SessionMessageMatch, SessionRecallMatch, SessionRecallStore
from .session_store import AgentSessionRecord, AgentSessionStore
from .tool_registry import (
    ToolHandler,
    ToolRegistry,
    normalize_tool_call,
    parse_tool_call_arguments,
    tool_definition_from_descriptor,
    tool_definition_to_openai,
)

__all__ = [
    "AgentLoop",
    "AgentLoopResult",
    "AgentSessionRecord",
    "AgentSessionStore",
    "HermesCapabilityMapping",
    "HermesFacade",
    "HermesMixedIntegrationPlan",
    "LLMExecutor",
    "PersistentMemorySnapshot",
    "PersistentMemoryStore",
    "SessionMessageMatch",
    "SessionRecallMatch",
    "SessionRecallStore",
    "ToolHandler",
    "ToolRegistry",
    "bind_session_context",
    "build_memory_message",
    "build_prompt_messages",
    "build_agent_plan",
    "build_plan_message",
    "create_meta_harness_tool_registry",
    "find_capability_mapping",
    "get_current_session_id",
    "get_capability_snapshot",
    "get_mixed_integration_plan",
    "get_memory_snapshot",
    "get_sessions_snapshot",
    "get_skills_snapshot",
    "get_tools_snapshot",
    "normalize_tool_call",
    "parse_tool_call_arguments",
    "tool_definition_from_descriptor",
    "tool_definition_to_openai",
]
