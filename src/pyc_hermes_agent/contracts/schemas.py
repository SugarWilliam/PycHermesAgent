"""Schema dataclasses for cross-layer runtime contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class TaskRequest:
    schema_version: str = "1.0"
    task_id: str = field(default_factory=lambda: str(uuid4()))
    mode: str = "chat"
    input: Dict[str, Any] = field(default_factory=dict)
    context_refs: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    trace_level: str = "basic"


@dataclass(slots=True)
class ChatMessage:
    role: str = "user"
    content: str = ""
    tool_call_id: Optional[str] = None
    tool_calls: List[ToolCall] = field(default_factory=list)


@dataclass(slots=True)
class ChatCompletionRequest:
    schema_version: str = "1.0"
    model: str = ""
    messages: List[ChatMessage] = field(default_factory=list)
    tools: List[ToolDefinition] = field(default_factory=list)
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    timeout_seconds: float = 30.0
    retry_attempts: int = 1


@dataclass(slots=True)
class ChatCompletionResult:
    schema_version: str = "1.0"
    model: str = ""
    provider_id: str = ""
    content: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    finish_reason: Optional[str] = None
    usage: Dict[str, Any] = field(default_factory=dict)
    raw_response: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ChatCompletionChunk:
    schema_version: str = "1.0"
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


@dataclass(slots=True)
class AgentLoopEvent:
    schema_version: str = "1.0"
    event_id: str = field(default_factory=lambda: str(uuid4()))
    trace_id: str = ""
    sequence: int = 0
    event: str = "start"
    is_terminal: bool = False
    session_id: str = ""
    model: str = ""
    provider_id: str = ""
    iteration: int = 0
    retry_count: int = 0
    delta: str = ""
    content: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    finish_reason: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    error: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AgentLoopRequest:
    schema_version: str = "1.0"
    session_id: str = ""
    model: str = ""
    messages: List[ChatMessage] = field(default_factory=list)
    tools: List[ToolDefinition] = field(default_factory=list)
    activated_skills: List[str] = field(default_factory=list)
    planning_enabled: bool = True
    retry_budget: int = 1
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    timeout_seconds: float = 30.0
    retry_attempts: int = 1
    max_iterations: int = 8
    analysis_mode: str = "casual"
    # Session-scoped working memory (bounded; not MRAG-indexed). When ``update_working_memory`` is
    # true, request ``working_memory`` replaces the stored lines for this session on persist.
    working_memory: List[str] = field(default_factory=list)
    update_working_memory: bool = False

    def __post_init__(self) -> None:
        _allowed = ("casual", "structured", "formal")
        if self.analysis_mode not in _allowed:
            raise ValueError(f"AgentLoopRequest.analysis_mode must be one of: {', '.join(_allowed)}")
        if self.max_iterations < 1:
            raise ValueError("AgentLoopRequest.max_iterations must be >= 1")
        if self.retry_budget < 0:
            raise ValueError("AgentLoopRequest.retry_budget must be >= 0")


@dataclass(slots=True)
class PlanStep:
    schema_version: str = "1.0"
    step_id: str = ""
    kind: str = "respond"
    description: str = ""


@dataclass(slots=True)
class AgentPlan:
    schema_version: str = "1.0"
    summary: str = ""
    steps: List[PlanStep] = field(default_factory=list)


@dataclass(slots=True)
class AgentLoopResult:
    schema_version: str = "1.0"
    session_id: str = ""
    model: str = ""
    provider_id: str = ""
    content: str = ""
    finish_reason: Optional[str] = None
    iterations: int = 0
    retry_count: int = 0
    plan: Optional[AgentPlan] = None
    messages: List[ChatMessage] = field(default_factory=list)
    tool_results: List[ToolCallResult] = field(default_factory=list)
    working_memory: List[str] = field(default_factory=list)

    raw_response: Dict[str, Any] = field(default_factory=dict)

    audit: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolDefinition:
    schema_version: str = "1.0"
    type: str = "function"
    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=lambda: {"type": "object", "properties": {}})
    strict: bool = False


@dataclass(slots=True)
class ToolCall:
    schema_version: str = "1.0"
    id: str = field(default_factory=lambda: str(uuid4()))
    type: str = "function"
    name: str = ""
    arguments: str = "{}"


@dataclass(slots=True)
class ToolCallResult:
    schema_version: str = "1.0"
    tool_call_id: str = ""
    name: str = ""
    content: str = ""
    is_error: bool = False
    structured_content: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TaskResult:
    schema_version: str = "1.0"
    task_id: str = ""
    status: str = "success"
    summary: str = ""
    outputs: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    trace_ref: Optional[str] = None


@dataclass(slots=True)
class MetaAnalysisRequest:
    schema_version: str = "1.0"
    problem_statement: str = ""
    domain_hints: List[str] = field(default_factory=list)
    data_refs: List[str] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)
    objectives: List[str] = field(default_factory=list)
    allowed_methods: List[str] = field(default_factory=list)
    target_evidence_grade: str = "CE-C1"
    # SR dimension override for formal runs (empty = computed by MetaHarness SR policy).
    target_sr_grade: str = ""
    # Optional routing overlays: keyword_boosts, data_shape_bonus, data_shape_rules, pin_method, …
    meta_routing: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.problem_statement, str) or not self.problem_statement.strip():
            raise ValueError("MetaAnalysisRequest.problem_statement must be a non-empty string")


@dataclass(slots=True)
class MetaAnalysisResult:
    schema_version: str = "1.0"
    selected_method: str = ""
    method_rationale: str = ""
    assumptions: List[str] = field(default_factory=list)
    logic_review: List[str] = field(default_factory=list)
    reasonableness_review: List[str] = field(default_factory=list)
    evidence_grade: str = "CE-C1"
    sr_grade: str = "SR-C1"
    degraded: bool = False
    risks: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    execution_details: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EventEnvelope:
    schema_version: str = "1.0"
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=utc_now_iso)
    source: str = "sidecar"
    type: str = "task.progress"
    task_id: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ErrorEnvelope:
    schema_version: str = "1.0"
    code: str = "UNKNOWN"
    category: str = "internal"
    domain: str = "internal"
    message: str = ""
    retryable: bool = False
    degraded: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CapabilityDescriptor:
    schema_version: str = "1.0"
    id: str = ""
    kind: str = "adapter"
    input_schema: str = ""
    output_schema: str = ""
    dependencies: List[str] = field(default_factory=list)
    max_evidence_grade: str = "CE-C1"


@dataclass(slots=True)
class HermesSurface:
    schema_version: str = "1.0"
    id: str = ""
    kind: str = "capability"
    path: str = ""
    available: bool = False
    required: bool = False


@dataclass(slots=True)
class HermesRuntimeSnapshot:
    schema_version: str = "1.0"
    upstream_root: str = ""
    checkout_present: bool = False
    git_dir_present: bool = False
    detected_commit: str = ""
    worktree_state: str = "unknown"
    import_ready: bool = False
    surfaces: List[HermesSurface] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass(slots=True)
class HermesIntegrationSnapshot:
    schema_version: str = "1.0"
    surface: str = ""
    integration_mode: str = "discovery-only"
    status: str = "placeholder"
    placeholder: bool = True
    bridge_ready: bool = False
    upstream_available: bool = False
    checkout_import_ready: bool = False
    worktree_state: str = "unknown"
    source_paths: List[str] = field(default_factory=list)
    required_surfaces: List[str] = field(default_factory=list)
    available_surfaces: List[str] = field(default_factory=list)
    detected_entrypoints: List[str] = field(default_factory=list)
    planned_operations: List[str] = field(default_factory=list)
    discovered_count: int = 0
    sample_paths: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass(slots=True)
class HermesSkillDescriptor:
    schema_version: str = "1.0"
    id: str = ""
    name: str = ""
    description: str = ""
    path: str = ""
    source: str = "bundled"
    category: str = ""
    license: Optional[str] = None
    compatibility: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)
    loadable: bool = False
    parse_error: Optional[str] = None


@dataclass(slots=True)
class HermesSkillsSnapshot:
    schema_version: str = "1.0"
    integration: HermesIntegrationSnapshot = field(default_factory=lambda: HermesIntegrationSnapshot(surface="skills"))
    discovery_roots: List[str] = field(default_factory=list)
    skills: List[HermesSkillDescriptor] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass(slots=True)
class HermesSessionOperation:
    schema_version: str = "1.0"
    name: str = ""
    category: str = "lifecycle"
    available: bool = False


@dataclass(slots=True)
class HermesSessionStoreDescriptor:
    schema_version: str = "1.0"
    path_hint: str = ""
    schema_version_number: Optional[int] = None
    backend: str = "sqlite"
    tables: List[str] = field(default_factory=list)
    indexes: List[str] = field(default_factory=list)
    features: List[str] = field(default_factory=list)


@dataclass(slots=True)
class HermesSessionsSnapshot:
    schema_version: str = "1.0"
    integration: HermesIntegrationSnapshot = field(default_factory=lambda: HermesIntegrationSnapshot(surface="sessions"))
    store: HermesSessionStoreDescriptor = field(default_factory=HermesSessionStoreDescriptor)
    entrypoints: List[str] = field(default_factory=list)
    operations: List[HermesSessionOperation] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass(slots=True)
class HermesToolOperation:
    schema_version: str = "1.0"
    name: str = ""
    category: str = "discovery"
    available: bool = False


@dataclass(slots=True)
class HermesToolRegistryDescriptor:
    schema_version: str = "1.0"
    registry_path: str = ""
    toolsets_path: str = ""
    discovery_roots: List[str] = field(default_factory=list)
    legacy_toolset_aliases: List[str] = field(default_factory=list)
    public_api: List[str] = field(default_factory=list)
    features: List[str] = field(default_factory=list)


@dataclass(slots=True)
class HermesToolDescriptor:
    schema_version: str = "1.0"
    id: str = ""
    name: str = ""
    path: str = ""
    source: str = "builtin"
    toolset_hints: List[str] = field(default_factory=list)
    requires_env: List[str] = field(default_factory=list)
    registration_style: str = "unknown"
    registered: bool = False
    parse_error: Optional[str] = None


@dataclass(slots=True)
class HermesToolsSnapshot:
    schema_version: str = "1.0"
    integration: HermesIntegrationSnapshot = field(default_factory=lambda: HermesIntegrationSnapshot(surface="tools"))
    registry: HermesToolRegistryDescriptor = field(default_factory=HermesToolRegistryDescriptor)
    operations: List[HermesToolOperation] = field(default_factory=list)
    tools: List[HermesToolDescriptor] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass(slots=True)
class HermesMemoryOperation:
    schema_version: str = "1.0"
    name: str = ""
    category: str = "prefetch"
    available: bool = False


@dataclass(slots=True)
class HermesMemoryProviderDescriptor:
    schema_version: str = "1.0"
    id: str = ""
    name: str = ""
    path: str = ""
    source: str = "builtin"
    provider_kind: str = "plugin"
    loadable: bool = False
    hooks: List[str] = field(default_factory=list)
    config_fields: List[str] = field(default_factory=list)
    parse_error: Optional[str] = None


@dataclass(slots=True)
class HermesMemoryManagerDescriptor:
    schema_version: str = "1.0"
    manager_path: str = ""
    provider_base_path: str = ""
    public_api: List[str] = field(default_factory=list)
    helper_functions: List[str] = field(default_factory=list)
    features: List[str] = field(default_factory=list)
    plugin_roots: List[str] = field(default_factory=list)


@dataclass(slots=True)
class HermesMemorySnapshot:
    schema_version: str = "1.0"
    integration: HermesIntegrationSnapshot = field(default_factory=lambda: HermesIntegrationSnapshot(surface="memory"))
    manager: HermesMemoryManagerDescriptor = field(default_factory=HermesMemoryManagerDescriptor)
    operations: List[HermesMemoryOperation] = field(default_factory=list)
    providers: List[HermesMemoryProviderDescriptor] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass(slots=True)
class ModelAssetManifest:
    manifest_version: int = 1
    asset_id: str = ""
    kind: str = "embedding"
    version: str = ""
    checksum: str = ""
    size_bytes: int = 0
    compatible_app_range: str = ">=0.2,<0.3"
    compatible_index_format: int = 1


@dataclass(slots=True)
class KnowledgeDocument:
    schema_version: str = "1.0"
    document_id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    source_type: str = "text"
    source_uri: str = ""
    text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DocumentChunk:
    schema_version: str = "1.0"
    chunk_id: str = field(default_factory=lambda: str(uuid4()))
    document_id: str = ""
    index: int = 0
    text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RetrievalRequest:
    schema_version: str = "1.0"
    query: str = ""
    knowledge_base_ids: List[str] = field(default_factory=list)
    modalities: List[str] = field(default_factory=lambda: ["text"])
    top_k: int = 5
    include_citations: bool = True
    #: lexical | semantic | hybrid — hybrid combines normalized lexical with semantic-style trigram vectors.
    retrieval_mode: str = "lexical"
    #: Weight for semantic component in hybrid mode (0..1). Ignored when retrieval_mode is lexical or semantic.
    semantic_weight: float = 0.35
    #: empty → follow ``PYC_HERMES_MRAG_EMBEDDING_BACKEND``; trigram → deterministic hashed trigrams;
    #: sentence_transformer / dense → optional ``sentence-transformers`` encoder when installed.
    embedding_backend: str = ""


@dataclass(slots=True)
class Citation:
    schema_version: str = "1.0"
    document_id: str = ""
    chunk_id: str = ""
    title: str = ""
    source_type: str = ""
    source_uri: str = ""
    page: Optional[int] = None
    section: str = ""
    relevance: float = 0.0
    snippet: str = ""


@dataclass(slots=True)
class RetrievalHit:
    schema_version: str = "1.0"
    document_id: str = ""
    chunk_id: str = ""
    score: float = 0.0
    snippet: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RetrievalResult:
    schema_version: str = "1.0"
    hits: List[RetrievalHit] = field(default_factory=list)
    citations: List[Citation] = field(default_factory=list)
    coverage: float = 0.0
    confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)
