"""Core data structures for the LLM gateway."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from pyc_hermes_agent.contracts import ToolCall, ToolDefinition


@dataclass(slots=True)
class AuthMethodSpec:
    id: str
    label: str
    kind: str
    enterprise_supported: bool = False


@dataclass(slots=True)
class ModelVariantSpec:
    id: str
    options: Dict[str, Any] = field(default_factory=dict)
    disabled: bool = False


@dataclass(slots=True)
class ModelSpec:
    id: str
    provider_id: str
    model_id: str
    name: str
    tags: List[str] = field(default_factory=list)
    free: bool = False
    supports_tools: bool = True
    supports_vision: bool = False
    supports_reasoning: bool = False
    options: Dict[str, Any] = field(default_factory=dict)
    variants: Dict[str, ModelVariantSpec] = field(default_factory=dict)
    disabled: bool = False
    featured_rank: int = 999
    source: str = "builtin"


@dataclass(slots=True)
class ProviderSpec:
    id: str
    name: str
    auth_methods: List[AuthMethodSpec] = field(default_factory=list)
    default_model_id: Optional[str] = None
    default_small_model_id: Optional[str] = None
    first_class: bool = False
    free_first: bool = False
    source: str = "builtin"


@dataclass(slots=True)
class ProviderConfig:
    provider_id: str
    name: Optional[str] = None
    npm: Optional[str] = None
    base_url: Optional[str] = None
    headers: Dict[str, Any] = field(default_factory=dict)
    options: Dict[str, Any] = field(default_factory=dict)
    model_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass(slots=True)
class ResolvedLLMConfig:
    config_path: Optional[Path]
    raw_config: Dict[str, Any]
    providers: Dict[str, ProviderSpec]
    provider_configs: Dict[str, ProviderConfig]
    models: List[ModelSpec]
    default_model: str
    small_model: Optional[str]
    free_first: bool = True


@dataclass(slots=True)
class LLMMessage:
    role: str
    content: str
    tool_call_id: Optional[str] = None
    tool_calls: List[ToolCall] = field(default_factory=list)


@dataclass(slots=True)
class LLMChatRequest:
    model: str = ""
    messages: List[LLMMessage] = field(default_factory=list)
    tools: List[ToolDefinition] = field(default_factory=list)
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    timeout_seconds: float = 30.0
    retry_attempts: int = 1


@dataclass(slots=True)
class LLMChatResponse:
    model: str = ""
    provider_id: str = ""
    content: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    finish_reason: Optional[str] = None
    usage: Dict[str, Any] = field(default_factory=dict)
    raw_response: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LLMChatChunk:
    event: str = "delta"
    model: str = ""
    provider_id: str = ""
    delta: str = ""
    content: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    finish_reason: Optional[str] = None
    usage: Dict[str, Any] = field(default_factory=dict)
    error: Dict[str, Any] = field(default_factory=dict)
    raw_response: Dict[str, Any] = field(default_factory=dict)
