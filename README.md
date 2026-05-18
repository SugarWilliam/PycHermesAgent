# PycHermesAgent

> Status: internal engineering preview. Not production-ready.

PycHermesAgent is a local-first agent platform baseline built around:

1. `hermes_engine`
2. `meta_harness`
3. `llm_gateway`
4. `mrag_core`
5. a Python sidecar contract surface

Current repository status:

1. Governance and architecture baseline are in place.
2. Contract-tested Python sidecar functions are implemented.
3. Hermes read-only bridge snapshots are implemented.
4. A minimal local HTTP sidecar transport is implemented.
5. A minimal OpenAI-compatible synchronous LLM execution path is implemented.
6. Minimal local model-asset promotion and artifact export helpers are implemented.
7. CI (GitHub Actions) runs contract tests and `scripts/release_gates.py`; a minimal Electron preview shell lives under `desktop/` (does not bundle Python).

## Continuous integration

Push and pull requests to `main` run **`.github/workflows/ci.yml`** (Python 3.11 and 3.12): `pip install -e ".[dev]"`, **`pyc-hermes-packaging-probe`** under a simulated Windows-style layout, `scripts/release_gates.py` (contract tests + whitespace + heuristic secret scan).

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

## Key Documents

- `docs/assessment/Reassessment_v4_FactChecked_and_Upgraded.md` — architecture/评估 **事实校对** 稿
- `docs/architecture/Phase2_Toward_GA_v0.2.1.md` — Phase 2 朝向 GA / 生产 / 商业 **工作草案**
- `docs/deployment/Windows_Sidecar_Binary.md` — Windows 侧车 **PyInstaller** 产物说明
- `docs/architecture/PycHermesAgent_Architecture_v0.2.0.md`
- `docs/architecture/PycHermesAgent_Solution_Architecture_v0.2.0.md`
- `docs/architecture/Execution_Blueprint_v0.2.0.md`
- `docs/architecture/Hermes_Mixed_Integration_Mapping_v0.2.0.md`
- `docs/architecture/Phase1_Roadmap_v0.2.0.md`
- `docs/design/PycHermesAgent_Detailed_Design_v0.2.0.md`
- `docs/features/PycHermesAgent_Feature_Details_v0.2.0.md`
- `docs/deployment/PycHermesAgent_Usage_Deployment_Guide_v0.2.0.md`

## Release Status

Tagged releases (**`v*.*.*`**) trigger **`.github/workflows/release.yml`**, which builds **`pyc-hermes-sidecar.exe`** (Windows) and publishes a **GitHub Release** with checksums. Release notes stub: `docs/releases/v0.2.1.md`.

The repository is suitable for architecture validation, contract validation, and internal engineering preview work.
It is not yet a production release.
