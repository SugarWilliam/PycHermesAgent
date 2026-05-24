# PycHermesAgent

> Status: internal engineering preview. Not production-ready.

PycHermesAgent is a Windows-first, local-first agent platform built around:

1. `hermes_engine`
2. `meta_harness`
3. `llm_gateway`
4. `mrag_core`
5. `sidecar_api`
6. an Electron desktop shell under `desktop/`

Current repository baseline:

1. Governance, architecture, compatibility, and packaging constraints are in place under `AGENTS.md` and `docs/`.
2. Contract-tested Python sidecar routes are implemented, including JSON and SSE agent-loop surfaces.
3. Product-owned `hermes_engine.AgentLoop` is implemented with tool dispatch, session persistence, retry budgeting, and analysis-mode support. Default `create_meta_harness_tool_registry()` tools include **`formal_analysis`**, **`web_search`**, and **`knowledge_retrieve`** (local MRAG search bound to workspace root).
4. `meta_harness.MetaFramework.execute()` remains the formal-analysis entry point.
5. The Electron desktop is a usable preview workbench with streaming chat, sessions, settings, citations, and a main-process-owned sidecar startup contract.
6. `scripts/release_gates.py` is the local verification baseline for the repository.
7. **`web_search` resilience (Track B):** TTL on-disk cache (under packaging ``cache/web_search``), per-process minute/hour quotas, provider backoff, and ``meta`` telemetry such as ``latency_ms`` / ``cache_hit`` / ``quota_remaining_*`` (`hermes_engine/web_search_runtime.py`). The tool accepts optional JSON ``workspace_root`` to sandbox cache paths consistently with the writable layout.
8. **MRAG hybrid semantics:** deterministic trigram embeddings remain default; installing ``pip install -e '.[mrag-dense]'`` unlocks sentence-transformers encoders selectable via ``PYC_HERMES_MRAG_EMBEDDING_BACKEND`` (or ``RetrievalRequest.embedding_backend`` per call). Missing deps fall back gracefully with retrieval warnings (`mrag_core/embedding_backend.py`).
9. **Skills governance (Track D):** SKILL front matter supports numeric ``priority`` (controls activation ordering + system prompt stacking) and ``overlap_group`` (multi-skill overlaps surface hints under ``AgentLoop`` audit payloads via `skill_runtime_audit.py`).
10. **Deterministic benchmarks:** synthetic lexical/hybrid regressions (`benchmarks/mrag/run_expanded_hybrid_benchmark.py`) plus IPC-oriented shaped corpora (`benchmarks/mrag/run_ipc_business_hybrid_benchmark.py`, also wired into production release gates).

## Continuous integration

Push and pull requests to `main` run **`.github/workflows/ci.yml`**: **Python 3.11 + 3.12** MRAG proofs + **`pyc-hermes-packaging-probe`** + **`scripts/release_gates.py`** (pytest + whitespace + secret heuristics + ruff/mypy as configured); **`production-gates`** (Ubuntu ``RELEASE_GATES_PRODUCTION=1`` + Linux **`dist:dir`** + electron smoke); **`desktop-windows-unpacked`** (``win-unpacked`` + smoke); and **`desktop-windows-nsis-silent`** (dual semver NSIS **`dist:win`** builds + PREFIX upgrade + uninstall via `scripts/windows_nsis_silent_upgrade_smoke.ps1`). Use **`uv`** locally as in `scripts/release_gates.py`; CI uses **`uv sync --extra dev`**. Signing, **electron-updater feed** proof, and store-ready releases remain release governance (`release.yml`, `docs/deployment/Production_Release_Gates.md`).

## Quick Start

Install in editable mode:

```powershell
python -m pip install -e .
```

For contributors running tests and release gates locally:

```powershell
python -m pip install -e ".[dev]"
./.venv/bin/python scripts/release_gates.py
```

Run contract tests only:

```powershell
python -m pytest tests/contract
```

Run the local sidecar HTTP server (editable install / dev; writable sandbox under `--root`):

```powershell
pyc-hermes-sidecar --host 127.0.0.1 --port 8765
```

Windows **read-only install preview** (writable data in `%LOCALAPPDATA%` / `%APPDATA%`, not under the repo): see `packaging/windows/README.md` and use `Run-SidecarPreview.ps1`.

Inspect resolved directories (JSON):

```powershell
pyc-hermes-packaging-probe --mkdirs
```

Read health from Python:

```python
from pyc_hermes_agent import SidecarClient

status = SidecarClient().get_health_status()
print(status.status_label)
```

Read health over HTTP:

```python
from pyc_hermes_agent import SidecarClient

status = SidecarClient(base_url="http://127.0.0.1:8765").get_health_status()
print(status.status_label)
```

Minimal LLM execution over the sidecar API:

```python
from pyc_hermes_agent import SidecarClient
from pyc_hermes_agent.contracts import ChatCompletionRequest, ChatMessage

client = SidecarClient()
result = client.invoke_chat_completion(
    ChatCompletionRequest(
        model="openai-compatible/demo-model",
        messages=[ChatMessage(role="user", content="Say hello")],
    )
)
print(result["content"])
```

## Document Roles

Use docs by authority level:

- Governance and architecture authority:
  - `AGENTS.md`
  - `docs/Project_Development_and_Release_Governance.md`
  - `docs/architecture/*.md`
  - `docs/constraints/*.md`
- Current contract and baseline truth:
  - `docs/architecture/Compatibility_Matrix.md`
  - `docs/deployment/Production_Release_Gates.md`
  - `docs/Documentation_Tracking.md`
- Status, release, and execution notes:
  - `docs/releases/*.md`
  - `docs/superpowers/specs/*.md`
  - `docs/superpowers/plans/*.md`

## Key Documents

- `docs/Documentation_Tracking.md` — `docs/` inventory and tracking index
- `docs/Project_Development_and_Release_Governance.md` — top-level development and release authority
- `docs/architecture/Compatibility_Matrix.md` — current contract and version baseline
- `docs/architecture/Phase3_Phase4_Productization_Roadmap_v0.3.0.md` — Phase 3 → 4 productization roadmap
- `docs/deployment/Production_Release_Gates.md` — current release-gate operations baseline
- `docs/deployment/Windows_Sidecar_Binary.md` — Windows sidecar PyInstaller artifact notes
- `docs/architecture/PycHermesAgent_Architecture_v0.2.0.md`
- `docs/architecture/PycHermesAgent_Solution_Architecture_v0.2.0.md`
- `docs/architecture/Execution_Blueprint_v0.2.0.md`
- `docs/architecture/Hermes_Mixed_Integration_Mapping_v0.2.0.md`
- `docs/design/PycHermesAgent_Detailed_Design_v0.2.0.md`
- `docs/features/PycHermesAgent_Feature_Details_v0.2.0.md`
- `docs/deployment/PycHermesAgent_Usage_Deployment_Guide_v0.2.0.md`

## Release Status

Tagged releases (**`v*.*.*`**) trigger **`.github/workflows/release.yml`**, which builds **`pyc-hermes-sidecar.exe`** (Windows) and publishes a **GitHub Release** with checksums. Current release-note workflow lives in `docs/releases/README.md`.

`docs/releases/v0.3.0.md` and `docs/releases/v0.2.1.md` are historical tag notes. For current repository truth, prefer `docs/architecture/Compatibility_Matrix.md` and `docs/deployment/Production_Release_Gates.md`.

The repository is suitable for architecture validation, contract validation, and internal engineering preview work.
It is not yet a production release.
