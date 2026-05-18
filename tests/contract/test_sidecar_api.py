from pathlib import Path

from pyc_hermes_agent.contracts import AgentLoopRequest, MetaAnalysisRequest
from pyc_hermes_agent.contracts import ModelAssetManifest, RetrievalRequest
from pyc_hermes_agent.asset_manager import AssetManager, calculate_asset_checksum
from pyc_hermes_agent.artifact_engine import ArtifactEngine
from pyc_hermes_agent.sidecar_api import (
    create_knowledge_base,
    get_config_snapshot,
    get_health,
    get_hermes_bridge_health,
    get_hermes_capability_snapshot,
    get_hermes_memory_snapshot,
    get_hermes_sessions_snapshot,
    get_hermes_skills_snapshot,
    get_hermes_tools_snapshot,
    get_meta_harness_benchmark_smoke,
    get_meta_harness_dependency_snapshot,
    get_meta_harness_value_proof_benchmark,
    ingest_file_document,
    ingest_text_document,
    ingest_url_document,
    invoke_formal_analysis,
    list_knowledge_bases,
    list_models,
    list_providers,
    list_asset_inventory,
    list_rules,
    list_sidecar_artifacts,
    list_skills,
    run_agent_loop,
    search_knowledge_base,
    stream_agent_loop,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_fake_hermes_checkout(root: Path, *, missing: set[str] | None = None) -> Path:
    missing = missing or set()
    upstream = root / "upstream" / "hermes-agent"
    _write(upstream / ".git" / "HEAD", "ref: refs/heads/main\n")
    _write(upstream / ".git" / "refs" / "heads" / "main", "abcdef1234567890abcdef1234567890abcdef12\n")

    file_map = {
        "run_agent.py": "class AIAgent:\n    pass\n",
        "model_tools.py": (
            "from tools.registry import discover_builtin_tools\n\n"
            "discover_builtin_tools()\n\n"
            "def get_all_tool_names():\n    return ['demo_tool']\n\n"
            "def get_toolset_for_tool(name):\n    return 'safe'\n\n"
            "def get_available_toolsets():\n    return {'safe': ['demo_tool']}\n\n"
            "def check_toolset_requirements():\n    return {}\n\n"
            "def check_tool_availability(quiet=False):\n    return [], []\n\n"
            "def get_tool_definitions(*args, **kwargs):\n    return []\n\n"
            "def handle_function_call(*args, **kwargs):\n    return '{}'\n"
            "_LEGACY_TOOLSET_MAP = {\n"
            "    'file_tools': ['read_file'],\n"
            "    'terminal_tools': ['terminal'],\n"
            "}\n"
        ),
        "tools/registry.py": (
            "class Registry:\n"
            "    def register(self, **kwargs):\n        return None\n\n"
            "registry = Registry()\n\n"
            "def discover_builtin_tools():\n    return []\n"
        ),
        "toolsets.py": (
            "def resolve_toolset(name):\n    return ['demo_tool']\n\n"
            "def validate_toolset(name):\n    return True\n\n"
            "TOOLSETS = {'safe': ['demo_tool']}\n"
        ),
        "hermes_constants.py": (
            "import os\n"
            "from pathlib import Path\n\n"
            "def get_hermes_home() -> Path:\n"
            "    return Path(os.environ.get('HERMES_HOME', '.'))\n"
        ),
        "hermes_state.py": (
            "from hermes_constants import get_hermes_home\n\n"
            "DEFAULT_DB_PATH = get_hermes_home() / 'state.db'\n"
            "SCHEMA_VERSION = 11\n"
            "SCHEMA_SQL = \"\"\"\n"
            "CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, parent_session_id TEXT, handoff_state TEXT);\n"
            "CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL);\n"
            "CREATE TABLE IF NOT EXISTS state_meta (key TEXT PRIMARY KEY, value TEXT);\n"
            "CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(id);\n"
            "\"\"\"\n"
            "FTS_SQL = \"\"\"\n"
            "CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(content);\n"
            "\"\"\"\n"
            "FTS_TRIGRAM_SQL = \"\"\"\n"
            "CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts_trigram USING fts5(content, tokenize='trigram');\n"
            "\"\"\"\n"
            "class SessionDB:\n"
            "    def __init__(self, db_path=None):\n"
            "        self.db_path = db_path or DEFAULT_DB_PATH\n"
            "        self._sessions = {}\n"
            "    def create_session(self, session_id: str, source: str, **kwargs):\n"
            "        self._sessions[session_id] = {'id': session_id, 'source': source}\n"
            "        return session_id\n"
            "    def get_session(self, session_id: str):\n        return self._sessions.get(session_id)\n"
            "    def resolve_session_id(self, session_id_or_prefix: str):\n"
            "        return session_id_or_prefix if session_id_or_prefix in self._sessions else None\n"
            "    def list_sessions_rich(self, *args, **kwargs):\n        return list(self._sessions.values())\n"
            "    def resolve_resume_session_id(self, session_id: str):\n        return session_id if session_id in self._sessions else None\n"
            "    def search_sessions(self, *args, **kwargs):\n        return []\n"
        ),
        "agent/memory_manager.py": (
            "# Only ONE external plugin provider is allowed\n"
            "def sanitize_context(text: str) -> str:\n    return text.replace('<memory-context>', '').replace('</memory-context>', '')\n\n"
            "def build_memory_context_block(raw_context: str) -> str:\n    return f'<memory-context>{raw_context}</memory-context>'\n\n"
            "class StreamingContextScrubber:\n"
            "    def feed(self, text: str) -> str:\n        return text\n"
            "    def flush(self) -> str:\n        return ''\n\n"
            "class MemoryManager:\n"
            "    def __init__(self):\n        self._providers = []\n"
            "    @property\n    def providers(self):\n        return list(self._providers)\n"
            "    def add_provider(self, provider):\n        return None\n"
            "    def get_provider(self, name: str):\n        return None\n"
            "    def build_system_prompt(self) -> str:\n        return ''\n"
            "    def prefetch_all(self, query: str, *, session_id: str = '') -> str:\n        return ''\n"
            "    def queue_prefetch_all(self, query: str, *, session_id: str = '') -> None:\n        return None\n"
            "    def sync_all(self, user_content: str, assistant_content: str, *, session_id: str = '') -> None:\n        return None\n"
            "    def get_all_tool_schemas(self):\n        return []\n"
            "    def route_tool_call(self, tool_name: str, args, **kwargs):\n        return '{}'\n"
            "    def shutdown_all(self) -> None:\n        return None\n"
        ),
        "agent/memory_provider.py": (
            "class MemoryProvider:\n"
            "    def is_available(self):\n        return True\n"
            "    def initialize(self, session_id: str, **kwargs):\n        return None\n"
            "    def system_prompt_block(self) -> str:\n        return ''\n"
            "    def prefetch(self, query: str, *, session_id: str = '') -> str:\n        return ''\n"
            "    def queue_prefetch(self, query: str, *, session_id: str = '') -> None:\n        return None\n"
            "    def sync_turn(self, user_content: str, assistant_content: str, *, session_id: str = '') -> None:\n        return None\n"
            "    def get_tool_schemas(self):\n        return []\n"
            "    def handle_tool_call(self, tool_name: str, args, **kwargs):\n        return '{}'\n"
            "    def shutdown(self) -> None:\n        return None\n"
            "    def get_config_schema(self):\n        return []\n"
            "    def save_config(self, values, hermes_home: str) -> None:\n        return None\n"
        ),
        "agent/skill_commands.py": "def get_skill_commands():\n    return {}\n",
        "tools/skills_tool.py": (
            "import json\n\n"
            "def skills_list(category: str = None, task_id: str = None) -> str:\n"
            "    skills = [\n"
            "        {'name': 'demo-skill', 'description': 'Demo skill description.', 'category': 'testing'}\n"
            "    ]\n"
            "    return json.dumps({\n"
            "        'success': True,\n"
            "        'skills': skills,\n"
            "        'categories': ['testing'],\n"
            "        'count': len(skills),\n"
            "    })\n"
        ),
        "skills/testing/demo/SKILL.md": (
            "---\n"
            "name: demo-skill\n"
            "description: Demo skill description.\n"
            "metadata:\n"
            "  category: testing\n"
            "---\n"
            "# Demo Skill\n"
        ),
        "tools/demo_tool.py": (
            "from tools.registry import registry\n\n"
            "registry.register(\n"
            "    name='demo_tool',\n"
            "    toolset='safe',\n"
            "    requires_env=['DEMO_TOKEN'],\n"
            "    schema={'name': 'demo_tool'},\n"
            "    handler=lambda args, **kw: '{}'\n"
            ")\n"
        ),
        "plugins/memory/demo/__init__.py": (
            "class DemoMemoryProvider:\n"
            "    def is_available(self):\n        return True\n"
            "    def initialize(self, session_id: str, **kwargs):\n        return None\n"
            "    def prefetch(self, query: str, *, session_id: str = '') -> str:\n        return ''\n"
            "    def sync_turn(self, user_content: str, assistant_content: str, *, session_id: str = '') -> None:\n        return None\n"
            "    def get_tool_schemas(self):\n        return []\n"
            "    def get_config_schema(self):\n        return [{'provider_api_key': {'description': 'key'}}]\n"
        ),
    }
    for relative_path, content in file_map.items():
        if relative_path in missing:
            continue
        _write(upstream / relative_path, content)
    return upstream


def test_sidecar_health() -> None:
    import sys

    health = get_health()
    assert health["healthy"] is True
    assert isinstance(health["degraded"], bool)
    assert health["status_label"] == health["hermes"]["status_label"]
    assert "version" in health
    assert health["python_version"] == f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    assert health["platform"] == sys.platform
    assert "hermes" in health
    assert health["hermes"]["ready_state"] in {"ready", "degraded", "unavailable"}
    assert health["hermes"]["status_label"] in {"ready", "ready-with-warnings", "degraded", "unavailable"}
    assert "bridge_ready" in health["hermes"]
    assert "bridged_surfaces" in health["hermes"]


def test_sidecar_health_includes_fake_hermes_bridge_summary(tmp_path: Path) -> None:
    _make_fake_hermes_checkout(tmp_path)

    health = get_health(tmp_path)

    assert health["healthy"] is True
    assert health["degraded"] is False
    assert health["status_label"] == "ready-with-warnings"
    assert health["hermes"]["checkout_present"] is True
    assert health["hermes"]["import_ready"] is True
    assert health["hermes"]["ready_state"] == "ready"
    assert health["hermes"]["status_label"] == "ready-with-warnings"
    assert health["hermes"]["bridge_ready"] is True
    assert health["hermes"]["bridged_count"] == 4
    assert health["hermes"]["surface_count"] == 4
    assert health["hermes"]["bridged_surfaces"] == ["memory", "sessions", "skills", "tools"]
    assert health["hermes"]["blocked_surfaces"] == []


def test_sidecar_health_reports_unavailable_when_checkout_missing(tmp_path: Path) -> None:
    health = get_health(tmp_path)

    assert health["healthy"] is True
    assert health["degraded"] is True
    assert health["status_label"] == "unavailable"
    assert health["hermes"]["checkout_present"] is False
    assert health["hermes"]["import_ready"] is False
    assert health["hermes"]["bridge_ready"] is False
    assert health["hermes"]["ready_state"] == "unavailable"
    assert health["hermes"]["status_label"] == "unavailable"


def test_sidecar_health_refreshes_when_upstream_state_changes(tmp_path: Path) -> None:
    first = get_health(tmp_path)
    _make_fake_hermes_checkout(tmp_path)
    second = get_health(tmp_path)

    assert first["status_label"] == "unavailable"
    assert second["status_label"] == "ready-with-warnings"
    assert second["hermes"]["bridge_ready"] is True


def test_sidecar_lists_providers_and_models() -> None:
    root = Path(__file__).resolve().parents[2]
    providers = list_providers(root)
    models = list_models(root)
    assert any(provider["id"] == "github-copilot" for provider in providers)
    assert any(model["free"] for model in models)


def test_sidecar_lists_rules_and_skills() -> None:
    root = Path(__file__).resolve().parents[2]
    rules = list_rules(root)
    skills = list_skills(root)
    assert any(rule["name"] == "AGENTS.md" for rule in rules)
    skill = next(item for item in skills if item["name"] == "meta-harness-governance")
    assert skill["runtime"]["policy"]["activation_mode"] == "explicit_only"
    assert skill["runtime"]["policy"]["script_execution"] == "disabled"
    assert skill["runtime"]["source"]["kind"] == "SKILL.md"
    assert "mtime_ns" in skill["runtime"]["source"]


def test_sidecar_lists_asset_inventory_and_artifacts(tmp_path: Path) -> None:
    payload = b"local-weights"
    manifest = ModelAssetManifest(
        asset_id="demo/asset",
        version="v1",
        checksum=calculate_asset_checksum(payload),
        size_bytes=len(payload),
    )
    AssetManager(root=tmp_path).install_bytes(manifest, payload, filename="w.bin")
    ArtifactEngine(root=tmp_path).export_text("task-a", "note.txt", "hello", media_type="text/plain")

    assets = list_asset_inventory(tmp_path)
    assert len(assets["items"]) == 1
    assert assets["items"][0]["asset_id"] == "demo/asset"
    assert assets["items"][0]["version"] == "v1"

    all_arts = list_sidecar_artifacts(tmp_path)
    assert all_arts["task_id"] is None
    assert len(all_arts["items"]) == 1
    assert all_arts["items"][0]["task_id"] == "task-a"

    scoped = list_sidecar_artifacts(tmp_path, task_id="task-a")
    assert scoped["task_id"] == "task-a"
    assert len(scoped["items"]) == 1


def test_sidecar_config_snapshot() -> None:
    root = Path(__file__).resolve().parents[2]
    snapshot = get_config_snapshot(root)
    assert snapshot["default_model"]
    assert snapshot["free_first"] is True


def test_sidecar_exposes_meta_harness_dependency_snapshot() -> None:
    snapshot = get_meta_harness_dependency_snapshot()

    assert snapshot["entrypoint"] == "MetaFramework.execute"
    assert snapshot["capability_count"] >= 1
    assert any(capability["id"] == "A-22" for capability in snapshot["capabilities"])


def test_sidecar_exposes_meta_harness_benchmark_smoke() -> None:
    smoke = get_meta_harness_benchmark_smoke()

    assert smoke["entrypoint"] == "MetaFramework.execute"
    assert smoke["passed"] is True
    assert smoke["failed_count"] == 0


def test_sidecar_exposes_meta_harness_value_proof_benchmark() -> None:
    report = get_meta_harness_value_proof_benchmark()

    assert report["entrypoint"] == "MetaFramework.execute"
    assert report["benchmark_id"] == "meta_harness.value_proof.v1"
    assert report["passed"] is True


def test_sidecar_hermes_capability_snapshot(tmp_path: Path) -> None:
    _make_fake_hermes_checkout(tmp_path)

    snapshot = get_hermes_capability_snapshot(tmp_path)

    assert snapshot["checkout_present"] is True
    assert snapshot["import_ready"] is True
    assert any(surface["id"] == "hermes.sessions" for surface in snapshot["surfaces"])


def test_sidecar_hermes_bridge_health_snapshot(tmp_path: Path) -> None:
    _make_fake_hermes_checkout(tmp_path)

    health = get_hermes_bridge_health(tmp_path)

    assert health["checkout_present"] is True
    assert health["import_ready"] is True
    assert health["bridge_ready"] is True
    assert health["bridged_count"] == 4
    assert health["bridged_surfaces"] == ["memory", "sessions", "skills", "tools"]
    assert health["blocked_surfaces"] == []
    assert health["surfaces"]["sessions"]["status"] == "bridged"
    assert health["surfaces"]["memory"]["status"] == "bridged"
    assert health["surfaces"]["skills"]["status"] == "bridged"
    assert health["surfaces"]["tools"]["status"] == "bridged"


def test_sidecar_hermes_placeholder_snapshots(tmp_path: Path) -> None:
    _make_fake_hermes_checkout(tmp_path)

    sessions = get_hermes_sessions_snapshot(tmp_path)
    memory = get_hermes_memory_snapshot(tmp_path)
    skills = get_hermes_skills_snapshot(tmp_path)
    tools = get_hermes_tools_snapshot(tmp_path)

    assert sessions["integration"]["surface"] == "sessions"
    assert sessions["integration"]["status"] == "bridged"
    assert sessions["integration"]["bridge_ready"] is True
    assert sessions["integration"]["placeholder"] is False
    assert "SessionDB" in sessions["entrypoints"]
    assert sessions["store"]["schema_version_number"] == 11
    assert "sessions" in sessions["store"]["tables"]
    assert any(operation["name"] == "search_sessions" and operation["available"] for operation in sessions["operations"])
    assert memory["integration"]["surface"] == "memory"
    assert memory["integration"]["status"] == "bridged"
    assert memory["integration"]["bridge_ready"] is True
    assert memory["integration"]["placeholder"] is False
    assert "single-external-provider" in memory["manager"]["features"]
    assert any(operation["name"] == "prefetch_all" and operation["available"] for operation in memory["operations"])
    assert any(provider["id"] == "demo" and provider["source"] == "plugin" for provider in memory["providers"])
    assert skills["integration"]["surface"] == "skills"
    assert skills["integration"]["status"] == "bridged"
    assert skills["integration"]["bridge_ready"] is True
    assert skills["integration"]["placeholder"] is False
    assert skills["integration"]["discovered_count"] >= 1
    assert skills["skills"][0]["name"] == "demo-skill"
    assert skills["skills"][0]["loadable"] is True
    assert tools["integration"]["surface"] == "tools"
    assert tools["integration"]["status"] == "bridged"
    assert tools["integration"]["bridge_ready"] is True
    assert tools["integration"]["placeholder"] is False
    assert tools["integration"]["upstream_available"] is True
    assert "builtin-discovery" in tools["registry"]["features"]
    assert any(operation["name"] == "get_tool_definitions" and operation["available"] for operation in tools["operations"])
    assert tools["tools"][0]["name"] == "demo_tool"
    assert tools["tools"][0]["requires_env"] == ["DEMO_TOKEN"]


def test_sidecar_hermes_tools_snapshot_blocks_without_registry(tmp_path: Path) -> None:
    _make_fake_hermes_checkout(tmp_path, missing={"tools/registry.py"})

    tools = get_hermes_tools_snapshot(tmp_path)

    assert tools["integration"]["status"] == "blocked"
    assert any("hermes.tool_registry" in warning for warning in tools["integration"]["warnings"])


def test_sidecar_formal_analysis_invocation() -> None:
    response = invoke_formal_analysis(
        MetaAnalysisRequest(
            problem_statement="network pagerank analysis",
            data={"adjacency": [[0.0, 1.0], [1.0, 0.0]]},
            params={"analysis": "pagerank"},
        )
    )
    assert "events" in response
    assert "result" in response
    assert response["analysis"]["selected_method"] == "A-22"


def test_sidecar_formal_analysis_returns_standard_error_response_on_failure(monkeypatch) -> None:
    from pyc_hermes_agent.sidecar_api import service as sidecar_service

    class _FailingFramework:
        def execute(self, request):
            raise RuntimeError("analysis exploded")

    monkeypatch.setattr(sidecar_service, "MetaFramework", lambda: _FailingFramework())

    response = invoke_formal_analysis(
        MetaAnalysisRequest(
            problem_statement="network pagerank analysis",
            data={"adjacency": [[0.0, 1.0], [1.0, 0.0]]},
            params={"analysis": "pagerank"},
        )
    )

    assert response["status"] == "error"
    assert response["error"]["code"] == "FORMAL_ANALYSIS_FAILED"
    assert response["error"]["category"] == "internal"
    assert response["error"]["domain"] == "meta_harness"
    assert response["error"]["retryable"] is False
    assert response["error"]["degraded"] is False
    assert response["events"][-1]["type"] == "task.failed"


def test_sidecar_agent_loop_runs_formal_analysis_tool() -> None:
    class _FakeAgentLoop:
        def __init__(self, *, root=None):
            self.root = root

        def run(self, request, *, max_iterations=8, session_id=None, planning_enabled=True, retry_budget=1):
            from pyc_hermes_agent.contracts import AgentLoopResult, ChatMessage, ToolCallResult

            assert planning_enabled is True
            assert retry_budget == 1
            return AgentLoopResult(
                session_id="session-1",
                model=request.model or "openai-compatible/demo-model",
                provider_id="openai-compatible",
                content="Completed formal analysis.",
                finish_reason="stop",
                iterations=2,
                retry_count=0,
                messages=[
                    ChatMessage(role="user", content="Run formal analysis"),
                    ChatMessage(role="assistant", content="", tool_calls=[]),
                    ChatMessage(role="tool", content='{"selected_method": "A-22"}', tool_call_id="call-1"),
                    ChatMessage(role="assistant", content="Completed formal analysis."),
                ],
                tool_results=[
                    ToolCallResult(
                        tool_call_id="call-1",
                        name="formal_analysis",
                        content='{"selected_method": "A-22"}',
                        structured_content={"selected_method": "A-22"},
                    )
                ],
                raw_response={"choices": []},
            )

    from pyc_hermes_agent.sidecar_api import service as sidecar_service

    original = sidecar_service.AgentLoop
    sidecar_service.AgentLoop = _FakeAgentLoop
    try:
        response = run_agent_loop(
            AgentLoopRequest(
                session_id="session-1",
                model="openai-compatible/demo-model",
                messages=[{"role": "user", "content": "Run formal analysis"}],
            )
        )
    finally:
        sidecar_service.AgentLoop = original

    assert response["session_id"] == "session-1"
    assert response["provider_id"] == "openai-compatible"
    assert response["content"] == "Completed formal analysis."
    assert response["iterations"] == 2
    assert response["retry_count"] == 0
    assert response["tool_results"][0]["structured_content"]["selected_method"] == "A-22"


def test_sidecar_passes_activated_skills_to_agent_loop() -> None:
    class _FakeAgentLoop:
        def __init__(self, *, root=None):
            self.root = root

        def run(self, request, *, max_iterations=8, session_id=None, planning_enabled=True, retry_budget=1, activated_skills=None):
            from pyc_hermes_agent.contracts import AgentLoopResult

            assert activated_skills == ["demo-skill"]
            return AgentLoopResult(
                session_id=session_id or "session-1",
                model=request.model or "openai-compatible/demo-model",
                provider_id="openai-compatible",
                content="Skill active.",
                finish_reason="stop",
                iterations=1,
            )

    from pyc_hermes_agent.sidecar_api import service as sidecar_service

    original = sidecar_service.AgentLoop
    sidecar_service.AgentLoop = _FakeAgentLoop
    try:
        response = run_agent_loop(
            AgentLoopRequest(
                session_id="session-1",
                model="openai-compatible/demo-model",
                messages=[{"role": "user", "content": "Use skill"}],
                activated_skills=["demo-skill"],
            )
        )
    finally:
        sidecar_service.AgentLoop = original

    assert response["content"] == "Skill active."


def test_sidecar_agent_loop_streams_events() -> None:
    class _FakeAgentLoop:
        def __init__(self, *, root=None):
            self.root = root

        def stream(self, request, *, max_iterations=8, session_id=None, planning_enabled=True, retry_budget=1):
            from pyc_hermes_agent.contracts import AgentLoopEvent, AgentLoopResult

            yield AgentLoopEvent(event_id="event-1", trace_id="trace-1", sequence=1, event="start", session_id=session_id or "session-1", model=request.model)
            yield AgentLoopEvent(
                event_id="event-2",
                trace_id="trace-1",
                sequence=2,
                event="assistant.tool_call.delta",
                session_id=session_id or "session-1",
                model=request.model,
                tool_calls=[{"id": "call-1", "name": "echo_text", "arguments": '{"text":"he'}],
            )
            yield AgentLoopEvent(
                event_id="event-3",
                trace_id="trace-1",
                sequence=3,
                event="assistant.delta",
                session_id=session_id or "session-1",
                model=request.model,
                delta="Hello",
            )
            yield AgentLoopEvent(
                event_id="event-4",
                trace_id="trace-1",
                sequence=4,
                event="done",
                is_terminal=True,
                session_id=session_id or "session-1",
                model=request.model,
                content="Hello",
                finish_reason="stop",
                payload={"result": AgentLoopResult(session_id=session_id or "session-1", model=request.model, content="Hello")},
            )

    from pyc_hermes_agent.sidecar_api import service as sidecar_service

    original = sidecar_service.AgentLoop
    sidecar_service.AgentLoop = _FakeAgentLoop
    try:
        events = list(
            stream_agent_loop(
                AgentLoopRequest(
                    session_id="session-1",
                    model="openai-compatible/demo-model",
                    messages=[{"role": "user", "content": "Hello"}],
                )
            )
        )
    finally:
        sidecar_service.AgentLoop = original

    assert events[0]["event"] == "start"
    assert events[0]["event_id"] == "event-1"
    assert events[0]["trace_id"] == "trace-1"
    assert events[0]["sequence"] == 1
    assert events[1]["event"] == "assistant.tool_call.delta"
    assert events[1]["tool_calls"][0]["name"] == "echo_text"
    assert events[2]["event"] == "assistant.delta"
    assert events[-1]["event"] == "done"
    assert events[-1]["is_terminal"] is True
    assert events[-1]["payload"]["result"]["content"] == "Hello"


def test_sidecar_agent_loop_stream_logs_finished_metadata(monkeypatch) -> None:
    log_calls: list[tuple[str, dict]] = []

    class _FakeAgentLoop:
        def __init__(self, *, root=None):
            self.root = root

        def stream(self, request, *, max_iterations=8, session_id=None, planning_enabled=True, retry_budget=1):
            from pyc_hermes_agent.contracts import AgentLoopEvent, AgentLoopResult

            yield AgentLoopEvent(event_id="event-1", trace_id="trace-1", sequence=1, event="start", session_id=session_id or "session-1", model=request.model)
            yield AgentLoopEvent(
                event_id="event-2",
                trace_id="trace-1",
                sequence=2,
                event="done",
                is_terminal=True,
                session_id=session_id or "session-1",
                model=request.model,
                provider_id="openai-compatible",
                iteration=2,
                finish_reason="stop",
                payload={"result": AgentLoopResult(session_id=session_id or "session-1", model=request.model, content="Hello")},
            )

    from pyc_hermes_agent.sidecar_api import service as sidecar_service

    monkeypatch.setattr(sidecar_service, "AgentLoop", _FakeAgentLoop)
    monkeypatch.setattr(sidecar_service, "log_event", lambda event, **fields: log_calls.append((event, fields)))

    events = list(
        stream_agent_loop(
            AgentLoopRequest(
                session_id="session-1",
                model="openai-compatible/demo-model",
                messages=[{"role": "user", "content": "Hello"}],
            )
        )
    )

    assert [event["event"] for event in events] == ["start", "done"]
    started = next(fields for event, fields in log_calls if event == "agent.loop.stream.started")
    finished = next(fields for event, fields in log_calls if event == "agent.loop.stream.finished")
    assert started["model"] == "openai-compatible/demo-model"
    assert finished["provider_id"] == "openai-compatible"
    assert finished["finish_reason"] == "stop"
    assert finished["iterations"] == 2
    assert finished["trace_id"] == "trace-1"
    assert finished["sequence"] == 2


def test_sidecar_agent_loop_stream_logs_failed_metadata_for_fallback_error(monkeypatch) -> None:
    log_calls: list[tuple[str, dict]] = []

    class _FakeAgentLoop:
        def __init__(self, *, root=None):
            self.root = root

        def stream(self, request, *, max_iterations=8, session_id=None, planning_enabled=True, retry_budget=1):
            raise RuntimeError("stream exploded")

    from pyc_hermes_agent.sidecar_api import service as sidecar_service

    monkeypatch.setattr(sidecar_service, "AgentLoop", _FakeAgentLoop)
    monkeypatch.setattr(sidecar_service, "log_event", lambda event, **fields: log_calls.append((event, fields)))

    events = list(
        stream_agent_loop(
            AgentLoopRequest(
                session_id="session-error",
                model="openai-compatible/demo-model",
                messages=[{"role": "user", "content": "Hello"}],
            )
        )
    )

    assert len(events) == 1
    assert events[0]["event"] == "error"
    assert events[0]["is_terminal"] is True
    assert events[0]["sequence"] == 1
    assert bool(events[0]["trace_id"])
    failed = next(fields for event, fields in log_calls if event == "agent.loop.stream.failed")
    assert failed["error"] == "stream exploded"
    assert failed["trace_id"] == events[0]["trace_id"]
    assert failed["sequence"] == events[0]["sequence"]


def test_sidecar_mrag_ingest_and_search(tmp_path: Path) -> None:
    kb = create_knowledge_base("sidecar-kb", root=tmp_path)
    assert kb["knowledge_base_id"]
    ingest_text_document(
        kb["knowledge_base_id"],
        "MetaHarness selects methods and MRAG packages evidence with citations.",
        title="MRAG Note",
        source_uri="memory://sidecar/1",
        root=tmp_path,
    )
    result = search_knowledge_base(
        kb["knowledge_base_id"],
        RetrievalRequest(query="evidence citations", top_k=2),
        root=tmp_path,
    )
    assert result["hits"]
    assert result["citations"]
    all_bases = list_knowledge_bases(root=tmp_path)
    assert any(item["knowledge_base_id"] == kb["knowledge_base_id"] for item in all_bases)


def test_sidecar_mrag_ingests_file_and_url_documents(tmp_path: Path) -> None:
    source_path = tmp_path / "note.md"
    source_path.write_text("# Source\nFile and URL MRAG ingest should be searchable.", encoding="utf-8")
    kb = create_knowledge_base("sources", root=tmp_path)

    file_document = ingest_file_document(kb["knowledge_base_id"], source_path, root=tmp_path)
    url_document = ingest_url_document(
        kb["knowledge_base_id"],
        "https://example.invalid/source",
        "URL MRAG ingest should also be searchable evidence.",
        title="URL Source",
        root=tmp_path,
    )
    result = search_knowledge_base(kb["knowledge_base_id"], RetrievalRequest(query="searchable evidence", top_k=5), root=tmp_path)

    assert file_document["source_type"] == "markdown"
    assert url_document["source_type"] == "url"
    assert {citation["source_uri"] for citation in result["citations"]} >= {str(source_path), "https://example.invalid/source"}
