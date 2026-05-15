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
7. Electron desktop and production runtime flows are not yet complete.

## Quick Start

Install in editable mode:

```powershell
python -m pip install -e .
```

Run contract tests:

```powershell
python -m pytest tests/contract
```

Run the local sidecar HTTP server:

```powershell
pyc-hermes-sidecar --host 127.0.0.1 --port 8765
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

- `docs/architecture/PycHermesAgent_Architecture_v0.2.0.md`
- `docs/architecture/PycHermesAgent_Solution_Architecture_v0.2.0.md`
- `docs/architecture/Execution_Blueprint_v0.2.0.md`
- `docs/architecture/Hermes_Mixed_Integration_Mapping_v0.2.0.md`
- `docs/architecture/Phase1_Roadmap_v0.2.0.md`
- `docs/design/PycHermesAgent_Detailed_Design_v0.2.0.md`
- `docs/features/PycHermesAgent_Feature_Details_v0.2.0.md`
- `docs/deployment/PycHermesAgent_Usage_Deployment_Guide_v0.2.0.md`

## Release Status

The repository is suitable for architecture validation, contract validation, and internal engineering preview work.
It is not yet a production release.
