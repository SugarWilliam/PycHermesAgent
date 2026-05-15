"""opencode-style LLM gateway for PycHermesAgent."""

from .config import find_opencode_like_config, load_opencode_like_config, resolve_opencode_like_config
from .runtime import execute_chat, stream_chat
from .resolver import resolve_llm_config, sort_models_free_first
from .rules import discover_rule_files
from .skill_metadata import SkillMetadata, parse_skill_metadata
from .skills import discover_skills, load_skill_metadata
from .types import LLMChatChunk, LLMChatRequest, LLMChatResponse, LLMMessage, ModelSpec, ProviderConfig, ProviderSpec, ResolvedLLMConfig

__all__ = [
    "discover_rule_files",
    "discover_skills",
    "execute_chat",
    "find_opencode_like_config",
    "LLMChatChunk",
    "LLMChatRequest",
    "LLMChatResponse",
    "LLMMessage",
    "load_opencode_like_config",
    "load_skill_metadata",
    "ModelSpec",
    "ProviderConfig",
    "ProviderSpec",
    "ResolvedLLMConfig",
    "resolve_llm_config",
    "resolve_opencode_like_config",
    "SkillMetadata",
    "stream_chat",
    "sort_models_free_first",
    "parse_skill_metadata",
]
