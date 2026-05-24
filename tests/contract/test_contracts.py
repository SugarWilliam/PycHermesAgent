from pyc_hermes_agent.contracts import (
    AgentLoopEvent,
    AgentLoopRequest,
    AgentLoopResult,
    AgentPlan,
    ChatCompletionChunk,
    ChatCompletionRequest,
    ChatMessage,
    CapabilityDescriptor,
    ErrorEnvelope,
    EventEnvelope,
    HermesIntegrationSnapshot,
    HermesMemoryManagerDescriptor,
    HermesMemoryOperation,
    HermesMemoryProviderDescriptor,
    HermesMemorySnapshot,
    HermesSessionOperation,
    HermesSessionsSnapshot,
    HermesSessionStoreDescriptor,
    HermesSkillDescriptor,
    HermesSkillsSnapshot,
    HermesToolDescriptor,
    HermesToolOperation,
    HermesToolRegistryDescriptor,
    HermesToolsSnapshot,
    KnowledgeDocument,
    MetaAnalysisRequest,
    RetrievalRequest,
    TaskRequest,
    ToolCall,
    ToolCallResult,
    ToolDefinition,
    PlanStep,
)


def test_task_request_defaults() -> None:
    request = TaskRequest()
    assert request.schema_version == "1.0"
    assert request.mode == "chat"
    assert request.task_id


def test_event_envelope_defaults() -> None:
    event = EventEnvelope(task_id="task-1")
    assert event.schema_version == "1.0"
    assert event.task_id == "task-1"
    assert event.timestamp


def test_chat_completion_request_defaults() -> None:
    request = ChatCompletionRequest(messages=[ChatMessage(content="hello")])
    assert request.schema_version == "1.0"
    assert request.tools == []
    assert request.timeout_seconds == 30.0
    assert request.retry_attempts == 1


def test_agent_loop_request_defaults() -> None:
    request = AgentLoopRequest(messages=[ChatMessage(content="hello")])
    assert request.schema_version == "1.0"
    assert request.session_id == ""
    assert request.planning_enabled is True
    assert request.retry_budget == 1
    assert request.max_iterations == 8
    assert request.tools == []
    assert request.working_memory == []
    assert request.update_working_memory is False


def test_agent_loop_result_defaults() -> None:
    result = AgentLoopResult(content="done")
    assert result.schema_version == "1.0"
    assert result.session_id == ""
    assert result.iterations == 0
    assert result.retry_count == 0
    assert result.plan is None
    assert result.tool_results == []
    assert result.working_memory == []


def test_chat_completion_chunk_defaults() -> None:
    chunk = ChatCompletionChunk()
    assert chunk.schema_version == "1.0"
    assert chunk.event == "delta"
    assert chunk.delta == ""
    assert chunk.tool_calls == []


def test_agent_loop_event_defaults() -> None:
    event = AgentLoopEvent()
    assert event.schema_version == "1.0"
    assert event.event_id
    assert event.trace_id == ""
    assert event.sequence == 0
    assert event.event == "start"
    assert event.is_terminal is False
    assert event.iteration == 0
    assert event.payload == {}


def test_agent_plan_defaults() -> None:
    plan = AgentPlan(summary="demo")
    assert plan.schema_version == "1.0"
    assert plan.summary == "demo"
    assert plan.steps == []


def test_plan_step_defaults() -> None:
    step = PlanStep(step_id="step-1", description="Do work")
    assert step.schema_version == "1.0"
    assert step.kind == "respond"


def test_tool_definition_defaults() -> None:
    definition = ToolDefinition(name="echo")
    assert definition.schema_version == "1.0"
    assert definition.type == "function"
    assert definition.parameters["type"] == "object"


def test_tool_call_defaults() -> None:
    call = ToolCall(name="echo")
    assert call.schema_version == "1.0"
    assert call.id
    assert call.arguments == "{}"


def test_tool_call_result_defaults() -> None:
    result = ToolCallResult(tool_call_id="call-1", name="echo")
    assert result.schema_version == "1.0"
    assert result.tool_call_id == "call-1"
    assert result.is_error is False


def test_capability_descriptor_fields() -> None:
    capability = CapabilityDescriptor(id="A-12-SCM", input_schema="a", output_schema="b")
    assert capability.id == "A-12-SCM"
    assert capability.max_evidence_grade == "CE-C1"


def test_meta_request_defaults() -> None:
    request = MetaAnalysisRequest(problem_statement="causal effect of x on y")
    assert request.target_evidence_grade == "CE-C1"
    assert request.target_sr_grade == ""
    assert request.meta_routing == {}


def test_retrieval_request_defaults() -> None:
    request = RetrievalRequest(query="hello world")
    assert request.top_k == 5
    assert request.include_citations is True
    assert request.retrieval_mode == "lexical"
    assert request.semantic_weight == 0.35


def test_knowledge_document_defaults() -> None:
    document = KnowledgeDocument(title="Doc", text="hello")
    assert document.document_id
    assert document.source_type == "text"


def test_hermes_integration_snapshot_defaults() -> None:
    snapshot = HermesIntegrationSnapshot(surface="sessions")
    assert snapshot.schema_version == "1.0"
    assert snapshot.integration_mode == "discovery-only"
    assert snapshot.status == "placeholder"
    assert snapshot.placeholder is True


def test_hermes_skills_snapshot_defaults() -> None:
    descriptor = HermesSkillDescriptor(id="testing/demo", name="demo")
    snapshot = HermesSkillsSnapshot(skills=[descriptor])
    assert snapshot.schema_version == "1.0"
    assert snapshot.integration.surface == "skills"
    assert snapshot.skills[0].id == "testing/demo"


def test_hermes_sessions_snapshot_defaults() -> None:
    operation = HermesSessionOperation(name="search_sessions", category="search", available=True)
    snapshot = HermesSessionsSnapshot(
        store=HermesSessionStoreDescriptor(schema_version_number=11),
        operations=[operation],
    )
    assert snapshot.schema_version == "1.0"
    assert snapshot.integration.surface == "sessions"
    assert snapshot.store.schema_version_number == 11
    assert snapshot.operations[0].available is True


def test_hermes_tools_snapshot_defaults() -> None:
    descriptor = HermesToolDescriptor(id="read_file", name="read_file")
    snapshot = HermesToolsSnapshot(
        registry=HermesToolRegistryDescriptor(registry_path="tools/registry.py"),
        operations=[HermesToolOperation(name="get_tool_definitions", available=True)],
        tools=[descriptor],
    )
    assert snapshot.schema_version == "1.0"
    assert snapshot.integration.surface == "tools"
    assert snapshot.registry.registry_path == "tools/registry.py"
    assert snapshot.tools[0].id == "read_file"


def test_hermes_memory_snapshot_defaults() -> None:
    descriptor = HermesMemoryProviderDescriptor(id="builtin", name="builtin")
    snapshot = HermesMemorySnapshot(
        manager=HermesMemoryManagerDescriptor(manager_path="agent/memory_manager.py"),
        operations=[HermesMemoryOperation(name="prefetch_all", available=True)],
        providers=[descriptor],
    )
    assert snapshot.schema_version == "1.0"
    assert snapshot.integration.surface == "memory"
    assert snapshot.manager.manager_path == "agent/memory_manager.py"
    assert snapshot.providers[0].id == "builtin"


def test_error_envelope_includes_domain_dimension() -> None:
    envelope = ErrorEnvelope(code="DEMO", category="internal", domain="meta_harness", message="m")
    assert envelope.schema_version == "1.0"
    assert envelope.domain == "meta_harness"
