"""Git metadata resolution and subprocess-based runtime probes."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def _resolve_upstream_root(root: Path | None = None, upstream_root: Path | None = None) -> Path:
    from .constants import _DEFAULT_UPSTREAM_RELATIVE
    from .discovery import _repo_root

    if upstream_root is not None:
        return upstream_root
    base = root or _repo_root()
    return base / _DEFAULT_UPSTREAM_RELATIVE


def _resolve_git_dir(repo_root: Path) -> Path | None:
    dot_git = repo_root / ".git"
    if dot_git.is_dir():
        return dot_git
    if not dot_git.is_file():
        return None

    try:
        raw = dot_git.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not raw.lower().startswith("gitdir:"):
        return None

    git_dir = Path(raw.split(":", 1)[1].strip())
    if not git_dir.is_absolute():
        git_dir = repo_root / git_dir
    return git_dir.resolve()


def _read_packed_ref(git_dir: Path, ref_name: str) -> str:
    packed_refs = git_dir / "packed-refs"
    if not packed_refs.exists():
        return ""

    try:
        lines = packed_refs.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""

    for line in lines:
        if not line or line.startswith("#") or line.startswith("^"):
            continue
        commit, _, ref = line.partition(" ")
        if ref.strip() == ref_name:
            return commit.strip()
    return ""


def _read_head_commit(git_dir: Path | None) -> str:
    if git_dir is None:
        return ""

    head_path = git_dir / "HEAD"
    if not head_path.exists():
        return ""

    try:
        head = head_path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    if not head:
        return ""
    if len(head) == 40 and all(char in "0123456789abcdef" for char in head.lower()):
        return head
    if not head.startswith("ref:"):
        return ""

    ref_name = head.split(":", 1)[1].strip()
    ref_path = git_dir / ref_name
    if ref_path.exists():
        try:
            return ref_path.read_text(encoding="utf-8").strip()
        except OSError:
            return ""
    return _read_packed_ref(git_dir, ref_name)


def _read_worktree_state(repo_root: Path, git_dir: Path | None) -> str:
    if not repo_root.exists():
        return "missing"
    if git_dir is None:
        return "unknown"

    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "status", "--short", "--untracked-files=normal"],
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"

    if result.returncode != 0:
        return "unknown"

    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        return "clean"

    deleted = sum(1 for line in lines if line[:2] in {"D ", " D"})
    untracked = sum(1 for line in lines if line.startswith("?? "))
    if deleted and untracked:
        return "inconsistent"
    return "dirty"


def _has_git_index_lock(git_dir: Path | None) -> bool:
    if git_dir is None:
        return False
    return (git_dir / "index.lock").exists()


def _read_json_line(text: str) -> dict[str, object] | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in reversed(lines):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


def _run_upstream_json_probe(
    upstream_root: Path,
    script: str,
    *,
    probe_name: str,
    env_updates: dict[str, str] | None = None,
) -> tuple[dict[str, object] | None, list[str]]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    if env_updates:
        env.update(env_updates)

    try:
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=str(upstream_root),
            env=env,
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, [f"Hermes {probe_name} runtime probe failed: {exc}."]

    payload = _read_json_line(result.stdout)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip() or f"exit code {result.returncode}"
        return None, [f"Hermes {probe_name} runtime probe failed: {detail}."]
    if payload is None:
        detail = result.stdout.strip() or result.stderr.strip() or "missing JSON payload"
        return None, [f"Hermes {probe_name} runtime probe failed: {detail}."]
    if payload.get("success") is not True:
        detail = str(payload.get("error") or f"{probe_name} probe returned success=false")
        return None, [f"Hermes {probe_name} runtime probe failed: {detail}."]
    return payload, []


def _probe_skills_runtime(upstream_root: Path) -> tuple[dict[str, object] | None, list[str]]:
    skills_tool = upstream_root / "tools" / "skills_tool.py"
    if not skills_tool.exists():
        return None, []

    script = (
        "import json, pathlib, sys;"
        "sys.path.insert(0, str(pathlib.Path('.').resolve()));"
        "from tools.skills_tool import skills_list;"
        "result = json.loads(skills_list());"
        "payload = {"
        "'success': bool(result.get('success')),"
        "'count': result.get('count'),"
        "'skills': result.get('skills') or [],"
        "'categories': result.get('categories') or [],"
        "'error': result.get('error')"
        "};"
        "print(json.dumps(payload, ensure_ascii=False))"
    )
    return _run_upstream_json_probe(
        upstream_root,
        script,
        probe_name="skills",
        env_updates={"HERMES_HOME": str(upstream_root)},
    )


def _probe_sessions_runtime(upstream_root: Path) -> tuple[dict[str, object] | None, list[str]]:
    hermes_state = upstream_root / "hermes_state.py"
    if not hermes_state.exists():
        return None, []

    with tempfile.TemporaryDirectory(prefix="pyc-hermes-session-probe-") as temp_dir:
        probe_db = Path(temp_dir) / "probe-state.db"
        script = (
            "import json, os, pathlib, sys;"
            "sys.path.insert(0, str(pathlib.Path('.').resolve()));"
            "from hermes_state import DEFAULT_DB_PATH, SCHEMA_VERSION, SessionDB;"
            "db_path = pathlib.Path(os.environ['PYC_HERMES_SESSION_PROBE_DB']);"
            "db = SessionDB(db_path=db_path);"
            "session_id = 'pyc-hermes-session-probe';"
            "created = db.create_session(session_id=session_id, source='cli');"
            "session = db.get_session(session_id);"
            "listed = db.list_sessions_rich(limit=5);"
            "resolved = db.resolve_session_id(session_id);"
            "resume = db.resolve_resume_session_id(session_id);"
            "payload = {"
            "'success': True,"
            "'schema_version': SCHEMA_VERSION,"
            "'default_db_path': str(DEFAULT_DB_PATH),"
            "'db_path': str(db_path),"
            "'created': created,"
            "'get_session_ok': bool(session),"
            "'list_count': len(listed),"
            "'resolved': resolved,"
            "'resume': resume"
            "};"
            "print(json.dumps(payload, ensure_ascii=False))"
        )
        return _run_upstream_json_probe(
            upstream_root,
            script,
            probe_name="sessions",
            env_updates={
                "HERMES_HOME": temp_dir,
                "PYC_HERMES_SESSION_PROBE_DB": str(probe_db),
            },
        )


def _probe_tools_runtime(upstream_root: Path) -> tuple[dict[str, object] | None, list[str]]:
    model_tools = upstream_root / "model_tools.py"
    if not model_tools.exists():
        return None, []

    with tempfile.TemporaryDirectory(prefix="pyc-hermes-tool-probe-") as temp_dir:
        script = (
            "import json, pathlib, sys;"
            "sys.path.insert(0, str(pathlib.Path('.').resolve()));"
            "import model_tools;"
            "tool_names = model_tools.get_all_tool_names();"
            "toolsets = model_tools.get_available_toolsets();"
            "requirements = model_tools.check_toolset_requirements();"
            "availability = model_tools.check_tool_availability(True);"
            "payload = {"
            "'success': True,"
            "'tool_count': len(tool_names),"
            "'tool_names': tool_names[:20],"
            "'toolset_count': len(toolsets),"
            "'toolset_names': list(toolsets.keys())[:20],"
            "'requirements_count': len(requirements),"
            "'availability_tuple_len': len(availability) if isinstance(availability, tuple) else 0"
            "};"
            "print(json.dumps(payload, ensure_ascii=False))"
        )
        return _run_upstream_json_probe(
            upstream_root,
            script,
            probe_name="tools",
            env_updates={"HERMES_HOME": temp_dir},
        )


def _probe_memory_runtime(upstream_root: Path) -> tuple[dict[str, object] | None, list[str]]:
    manager_path = upstream_root / "agent" / "memory_manager.py"
    if not manager_path.exists():
        return None, []

    with tempfile.TemporaryDirectory(prefix="pyc-hermes-memory-probe-") as temp_dir:
        script = (
            "import json, pathlib, sys;"
            "sys.path.insert(0, str(pathlib.Path('.').resolve()));"
            "from agent.memory_manager import MemoryManager, StreamingContextScrubber, build_memory_context_block, sanitize_context;"
            "manager = MemoryManager();"
            "prompt = manager.build_system_prompt();"
            "prefetch = manager.prefetch_all('probe', session_id='probe-session');"
            "schemas = manager.get_all_tool_schemas();"
            "scrubber = StreamingContextScrubber();"
            "visible = scrubber.feed('probe');"
            "flushed = scrubber.flush();"
            "fenced = build_memory_context_block('memo');"
            "payload = {"
            "'success': True,"
            "'provider_count': len(manager.providers),"
            "'prompt_empty': prompt == '',"
            "'prefetch_empty': prefetch == '',"
            "'schemas_count': len(schemas),"
            "'stream_visible': visible,"
            "'stream_flushed': flushed,"
            "'fenced_has_tag': '<memory-context>' in fenced,"
            "'sanitized': sanitize_context('<memory-context>x</memory-context>')"
            "};"
            "print(json.dumps(payload, ensure_ascii=False))"
        )
        return _run_upstream_json_probe(
            upstream_root,
            script,
            probe_name="memory",
            env_updates={"HERMES_HOME": temp_dir},
        )
