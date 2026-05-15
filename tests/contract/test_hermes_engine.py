from pathlib import Path

from pyc_hermes_agent.contracts import HermesMemorySnapshot, HermesSessionsSnapshot, HermesSkillsSnapshot, HermesToolsSnapshot
from pyc_hermes_agent.hermes_engine import (
    get_capability_snapshot,
    get_memory_snapshot,
    get_sessions_snapshot,
    get_skills_snapshot,
    get_tools_snapshot,
)


_FAKE_COMMIT = "1234567890abcdef1234567890abcdef12345678"


def _write(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_fake_hermes_checkout(root: Path, *, missing: set[str] | None = None) -> Path:
    missing = missing or set()
    upstream = root / "upstream" / "hermes-agent"

    _write(upstream / ".git" / "HEAD", "ref: refs/heads/main\n")
    _write(upstream / ".git" / "refs" / "heads" / "main", f"{_FAKE_COMMIT}\n")

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
            "CREATE TABLE IF NOT EXISTS sessions (\n"
            "    id TEXT PRIMARY KEY,\n"
            "    parent_session_id TEXT,\n"
            "    handoff_state TEXT\n"
            ");\n"
            "CREATE TABLE IF NOT EXISTS messages (\n"
            "    id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
            "    session_id TEXT NOT NULL\n"
            ");\n"
            "CREATE TABLE IF NOT EXISTS state_meta (\n"
            "    key TEXT PRIMARY KEY\n"
            ");\n"
            "CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(id);\n"
            "\"\"\"\n"
            "FTS_SQL = \"\"\"\n"
            "CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(content);\n"
            "\"\"\"\n"
            "FTS_TRIGRAM_SQL = \"\"\"\n"
            "CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts_trigram USING fts5(content, tokenize='trigram');\n"
            "\"\"\"\n"
            "def format_session_db_unavailable(prefix='Session database not available'):\n"
            "    return prefix\n\n"
            "class SessionDB:\n"
            "    def __init__(self, db_path=None):\n"
            "        self.db_path = db_path or DEFAULT_DB_PATH\n"
            "        self._sessions = {}\n"
            "    def create_session(self, session_id: str, source: str, **kwargs):\n"
            "        self._sessions[session_id] = {'id': session_id, 'source': source}\n"
            "        return session_id\n"
            "    def end_session(self, session_id: str, end_reason: str):\n        return None\n"
            "    def reopen_session(self, session_id: str):\n        return None\n"
            "    def get_session(self, session_id: str):\n        return self._sessions.get(session_id)\n"
            "    def resolve_session_id(self, session_id_or_prefix: str):\n        return session_id_or_prefix if session_id_or_prefix in self._sessions else None\n"
            "    def list_sessions_rich(self, *args, **kwargs):\n        return list(self._sessions.values())\n"
            "    def resolve_resume_session_id(self, session_id: str):\n        return session_id if session_id in self._sessions else None\n"
            "    def search_messages(self, *args, **kwargs):\n        return []\n"
            "    def search_sessions(self, *args, **kwargs):\n        return []\n"
            "    def set_session_title(self, session_id: str, title: str):\n        return True\n"
            "    def get_session_title(self, session_id: str):\n        return None\n"
            "    def get_session_by_title(self, title: str):\n        return None\n"
            "    def resolve_session_by_title(self, title: str):\n        return None\n"
            "    def request_handoff(self, session_id: str, platform: str):\n        return False\n"
            "    def get_handoff_state(self, session_id: str):\n        return None\n"
            "    def list_pending_handoffs(self):\n        return []\n"
            "    def claim_handoff(self, session_id: str):\n        return False\n"
            "    def complete_handoff(self, session_id: str):\n        return None\n"
            "    def fail_handoff(self, session_id: str, error: str):\n        return None\n"
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
        "agent/skill_commands.py": (
            "def _load_skill_payload(skill_identifier: str, task_id: str | None = None):\n"
            "    return None\n\n"
            "def get_skill_commands():\n    return {}\n"
        ),
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
        "cli.py": "class HermesCLI:\n    pass\n",
        "gateway/run.py": "class GatewayRunner:\n    pass\n",
        "skills/testing/demo/SKILL.md": (
            "---\n"
            "name: demo-skill\n"
            "description: Demo skill description.\n"
            "license: MIT\n"
            "compatibility: >=0.1\n"
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


def test_capability_snapshot_reports_ready_fake_checkout(tmp_path: Path) -> None:
    _make_fake_hermes_checkout(tmp_path)

    snapshot = get_capability_snapshot(root=tmp_path)

    surfaces = {surface.id: surface for surface in snapshot.surfaces}
    assert snapshot.checkout_present is True
    assert snapshot.detected_commit == _FAKE_COMMIT
    assert snapshot.import_ready is True
    assert surfaces["hermes.agent_loop"].available is True
    assert surfaces["hermes.tool_registry"].available is True
    assert surfaces["hermes.sessions"].available is True


def test_capability_snapshot_warns_when_required_surface_missing(tmp_path: Path) -> None:
    _make_fake_hermes_checkout(tmp_path, missing={"tools/registry.py"})

    snapshot = get_capability_snapshot(root=tmp_path)

    surfaces = {surface.id: surface for surface in snapshot.surfaces}
    assert snapshot.import_ready is False
    assert surfaces["hermes.tool_registry"].required is True
    assert surfaces["hermes.tool_registry"].available is False
    assert any("hermes.tool_registry" in warning for warning in snapshot.warnings)


def test_placeholder_snapshots_expose_detected_entrypoints(tmp_path: Path) -> None:
    _make_fake_hermes_checkout(tmp_path)

    sessions = get_sessions_snapshot(root=tmp_path)
    memory = get_memory_snapshot(root=tmp_path)
    skills = get_skills_snapshot(root=tmp_path)

    assert isinstance(sessions, HermesSessionsSnapshot)
    assert sessions.integration.status in {"placeholder", "bridged"}
    assert "SessionDB" in sessions.entrypoints
    assert sessions.store.schema_version_number == 11
    assert "sessions" in sessions.store.tables
    assert "fts5" in sessions.store.features
    assert any(operation.name == "search_sessions" and operation.available for operation in sessions.operations)
    assert isinstance(memory, HermesMemorySnapshot)
    assert memory.integration.upstream_available is True
    assert "memory-context-fencing" in memory.manager.features
    assert any(operation.name == "prefetch_all" and operation.available for operation in memory.operations)
    assert any(provider.id == "demo" for provider in memory.providers)
    assert isinstance(skills, HermesSkillsSnapshot)
    assert skills.integration.status in {"placeholder", "bridged"}
    assert skills.integration.discovered_count >= 1
    assert skills.discovery_roots == ["skills"]
    assert skills.skills[0].name == "demo-skill"
    assert skills.skills[0].loadable is True


def test_tools_placeholder_blocks_when_tool_registry_missing(tmp_path: Path) -> None:
    _make_fake_hermes_checkout(tmp_path, missing={"tools/registry.py"})

    tools = get_tools_snapshot(root=tmp_path)

    assert isinstance(tools, HermesToolsSnapshot)
    assert tools.integration.status == "blocked"
    assert tools.integration.upstream_available is False
    assert any("hermes.tool_registry" in warning for warning in tools.integration.warnings)


def test_sessions_snapshot_warns_when_schema_metadata_is_missing(tmp_path: Path) -> None:
    upstream = _make_fake_hermes_checkout(tmp_path)
    _write(
        upstream / "hermes_state.py",
        "def format_session_db_unavailable(prefix='Session database not available'):\n"
        "    return prefix\n\n"
        "class SessionDB:\n"
        "    def search_sessions(self, *args, **kwargs):\n        return []\n",
    )

    sessions = get_sessions_snapshot(root=tmp_path)

    assert sessions.store.schema_version_number is None
    assert any("schema version" in warning.lower() for warning in sessions.warnings)


def test_sessions_snapshot_marks_bridge_ready_when_upstream_runtime_probe_succeeds(tmp_path: Path) -> None:
    _make_fake_hermes_checkout(tmp_path)

    sessions = get_sessions_snapshot(root=tmp_path)

    assert sessions.integration.integration_mode == "subprocess-readonly"
    assert sessions.integration.status == "bridged"
    assert sessions.integration.placeholder is False
    assert sessions.integration.bridge_ready is True
    assert sessions.integration.discovered_count >= 1
    assert "SessionDB" in sessions.entrypoints


def test_tools_snapshot_reports_registry_and_discovered_tool_metadata(tmp_path: Path) -> None:
    _make_fake_hermes_checkout(tmp_path)

    tools = get_tools_snapshot(root=tmp_path)

    assert isinstance(tools, HermesToolsSnapshot)
    assert tools.integration.status == "bridged"
    assert tools.integration.integration_mode == "subprocess-readonly"
    assert tools.integration.bridge_ready is True
    assert "builtin-discovery" in tools.registry.features
    assert "file_tools" in tools.registry.legacy_toolset_aliases
    assert any(operation.name == "get_tool_definitions" and operation.available for operation in tools.operations)
    demo_tool = next(tool for tool in tools.tools if tool.name == "demo_tool")
    assert demo_tool.registered is True
    assert demo_tool.registration_style == "registry.register"
    assert demo_tool.requires_env == ["DEMO_TOKEN"]
    assert demo_tool.toolset_hints == ["safe"]


def test_tools_snapshot_marks_bridge_ready_when_upstream_runtime_probe_succeeds(tmp_path: Path) -> None:
    _make_fake_hermes_checkout(tmp_path)

    tools = get_tools_snapshot(root=tmp_path)

    assert tools.integration.integration_mode == "subprocess-readonly"
    assert tools.integration.status == "bridged"
    assert tools.integration.placeholder is False
    assert tools.integration.bridge_ready is True
    assert tools.integration.discovered_count >= 1


def test_memory_snapshot_reports_manager_and_plugin_metadata(tmp_path: Path) -> None:
    _make_fake_hermes_checkout(tmp_path)

    memory = get_memory_snapshot(root=tmp_path)

    assert isinstance(memory, HermesMemorySnapshot)
    assert memory.integration.status == "bridged"
    assert memory.integration.integration_mode == "subprocess-readonly"
    assert memory.integration.bridge_ready is True
    assert "single-external-provider" in memory.manager.features
    assert any(operation.name == "sync_all" and operation.available for operation in memory.operations)
    plugin = next(provider for provider in memory.providers if provider.id == "demo")
    assert plugin.source == "plugin"
    assert plugin.loadable is True
    assert "get_config_schema" in plugin.hooks


def test_memory_snapshot_marks_bridge_ready_when_upstream_runtime_probe_succeeds(tmp_path: Path) -> None:
    _make_fake_hermes_checkout(tmp_path)

    memory = get_memory_snapshot(root=tmp_path)

    assert memory.integration.integration_mode == "subprocess-readonly"
    assert memory.integration.status == "bridged"
    assert memory.integration.placeholder is False
    assert memory.integration.bridge_ready is True


def test_skills_snapshot_preserves_parse_errors_for_unloadable_skills(tmp_path: Path) -> None:
    upstream = _make_fake_hermes_checkout(tmp_path)
    _write(upstream / "skills" / "testing" / "broken" / "SKILL.md", "# Broken Skill\n")

    skills = get_skills_snapshot(root=tmp_path)

    broken = next(skill for skill in skills.skills if skill.id == "testing/broken")
    assert broken.loadable is False
    assert broken.parse_error == "Skill frontmatter missing."
    assert any("testing/broken/SKILL.md" in warning for warning in skills.warnings)


def test_skills_snapshot_marks_bridge_ready_when_upstream_runtime_probe_succeeds(tmp_path: Path) -> None:
    upstream = _make_fake_hermes_checkout(tmp_path)
    _write(
        upstream / "tools" / "skills_tool.py",
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
        "    })\n",
    )

    skills = get_skills_snapshot(root=tmp_path)

    assert skills.integration.integration_mode == "subprocess-readonly"
    assert skills.integration.status == "bridged"
    assert skills.integration.placeholder is False
    assert skills.integration.bridge_ready is True
    assert "skills_list" in skills.integration.detected_entrypoints
    assert skills.integration.discovered_count == 1
