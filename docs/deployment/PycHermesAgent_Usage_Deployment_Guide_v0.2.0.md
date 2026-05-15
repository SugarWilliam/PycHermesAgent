# PycHermesAgent Usage and Deployment Guide

| Field | Value |
| --- | --- |
| Date | 2026-05-15 |
| Version | v0.2.0 |
| Author | 彭耀成 |
| Status | Current Usage Guide and Deployment Boundary Document |

## Scope

This guide documents how the repository can be used today and what deployment modes are not yet available.

Current support level:

1. Local Python package usage
2. Contract and smoke test execution
3. In-process sidecar API calls
4. Minimal local HTTP sidecar transport
5. Minimal local-first MRAG persistence

Not yet supported as a finished product:

1. Electron desktop deployment
2. Production-grade standalone sidecar service deployment
3. Production LLM execution runtime
4. Production-grade persistent MRAG deployment

## Prerequisites

1. Windows or another Python 3.11+ development environment
2. Python 3.11 or newer
3. Access to the repository workspace

Optional but practically relevant dependencies for broader legacy-method coverage:

1. `numpy`
2. `pandas`
3. `scipy`
4. `statsmodels`

The current repository metadata in `pyproject.toml` now declares `numpy` as a core dependency and keeps the broader analysis stack as optional. This is still not a full production dependency profile.

## Local Development Setup

Example setup flow:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .
```

If you need broader legacy-method coverage, install the optional analysis extras manually.

Run the minimal local HTTP sidecar transport:

```powershell
pyc-hermes-sidecar --host 127.0.0.1 --port 8765
```

Example HTTP routes:

1. `GET /health`
2. `GET /hermes/bridge-health`
3. `POST /formal-analysis`
4. `POST /agent/run`
5. `POST /llm/chat/stream`
6. `POST /agent/run/stream`
7. `POST /knowledge-bases`
8. `POST /knowledge-bases/{id}/documents/text`
9. `POST /knowledge-bases/{id}/search`

## Basic Health Usage

Minimal product-facing health usage:

```python
from pyc_hermes_agent import SidecarClient

client = SidecarClient()
status = client.get_health_status()

print(status.status_label)
print(status.degraded)
```

Direct sidecar API usage:

```python
from pyc_hermes_agent.sidecar_api import get_health

health = get_health()
print(health["status_label"])
print(health["hermes"]["bridge_ready"])
```

Contract rule:

- Product consumers should key first-read health from top-level `status_label`.
- Nested `hermes` fields are diagnostic detail.

## Formal Analysis Usage

```python
from pyc_hermes_agent.contracts import MetaAnalysisRequest
from pyc_hermes_agent.sidecar_api import invoke_formal_analysis

request = MetaAnalysisRequest(
    problem_statement="network pagerank analysis",
    data={"adjacency": [[0.0, 1.0], [1.0, 0.0]]},
    params={"analysis": "pagerank"},
)

response = invoke_formal_analysis(request)
print(response["analysis"]["selected_method"])
```

Current deployment note:

- The formal analysis call itself still runs synchronously in the current process.
- The package now supports a minimal loopback HTTP transport for local engineering use.
- The transport is not yet hardened for production deployment.

## Agent Loop Usage

```python
from pyc_hermes_agent.contracts import AgentLoopRequest, ChatMessage
from pyc_hermes_agent.sidecar_api import run_agent_loop

request = AgentLoopRequest(
    model="openai-compatible/demo-model",
    messages=[ChatMessage(role="user", content="Run formal analysis for this task")],
    planning_enabled=True,
    retry_budget=1,
)

response = run_agent_loop(request)
print(response["content"])
print(response["iterations"])
print(response["retry_count"])
print(response["plan"]["summary"] if response["plan"] else "")
```

Current deployment note:

- The current loop is synchronous and bounded by `max_iterations`.
- Orchestration ownership remains in `hermes_engine`, with `sidecar_api` acting only as the exposure layer.
- `formal_analysis` is currently the builtin explicit capability available by default inside the loop.
- Session persistence, bounded prompt-time memory injection, minimal heuristic planning, and bounded recovery retries are now part of this API.
- Callers can set `planning_enabled=False` to suppress plan injection for a request.
- Callers can set `retry_budget` to control how many guided recovery retries may be used, and inspect `retry_count` in the result.
- Recovery prompts are transient runtime guidance and are not persisted into session history.
- Agent-loop streaming is available via `stream_agent_loop()` or `POST /agent/run/stream`, with assistant text emitted as deltas and tool/retry/lifecycle updates emitted as events.

## Agent Loop Streaming Usage

```python
from pyc_hermes_agent import SidecarClient
from pyc_hermes_agent.contracts import AgentLoopRequest, ChatMessage

client = SidecarClient()
for event in client.stream_agent_loop(
    AgentLoopRequest(
        model="openai-compatible/demo-model",
        messages=[ChatMessage(role="user", content="Run formal analysis for this task")],
        planning_enabled=True,
        retry_budget=1,
    )
):
    if event["event"] == "assistant.delta":
        print(event["delta"], end="")
    elif event["event"] == "assistant.tool_call.delta":
        print(event["tool_calls"][0]["name"])
    elif event["event"] == "tool.result":
        print(event["payload"]["tool_result"]["name"])
    elif event["event"] == "done":
        print(event["payload"]["result"]["content"])
    print(event["sequence"], event["trace_id"], event["is_terminal"])
```

Current deployment note:

- The current agent-loop streaming path forwards assistant text deltas and streamed tool-call formation when a streaming LLM executor is available.
- Tool results, retries, plans, and final completion remain event-oriented.
- The HTTP transport exposes this as `POST /agent/run/stream` using SSE.
- The same loop state machine underlies both `run_agent_loop()` and `stream_agent_loop()`.
- Each event now includes `event_id`, `trace_id`, monotonic `sequence`, and `is_terminal` so clients can correlate, order, and close streams deterministically.

## Chat Streaming Usage

```python
from pyc_hermes_agent import SidecarClient
from pyc_hermes_agent.contracts import ChatCompletionRequest, ChatMessage

client = SidecarClient()
for chunk in client.stream_chat_completion(
    ChatCompletionRequest(
        model="openai-compatible/demo-model",
        messages=[ChatMessage(role="user", content="Say hello")],
    )
):
    if chunk["event"] == "delta":
        print(chunk["delta"], end="")
    elif chunk["event"] == "done":
        print()
        print(chunk["content"])
```

Current deployment note:

- The current chat streaming path is separate from the agent-loop event stream.
- The HTTP transport exposes this as `POST /llm/chat/stream` using SSE.
- The current implementation is intentionally minimal and provider coverage remains narrow.

## Knowledge Retrieval Usage

```python
from pyc_hermes_agent.contracts import RetrievalRequest
from pyc_hermes_agent.sidecar_api import (
    create_knowledge_base,
    ingest_text_document,
    search_knowledge_base,
)

kb = create_knowledge_base("demo-kb")
ingest_text_document(
    kb["knowledge_base_id"],
    "MetaHarness selects methods and MRAG packages evidence with citations.",
    title="MRAG note",
)

result = search_knowledge_base(
    kb["knowledge_base_id"],
    RetrievalRequest(query="evidence citations", top_k=2),
)

print(len(result["hits"]))
```

Current limitation:

- Knowledge bases now persist across service restarts when a runtime storage root is active.
- Persistence is still MVP-grade JSON storage and should not be treated as a production database.

## Validation Commands

Current repository-level validation should focus on contract and smoke coverage.

Recommended commands:

```powershell
python -m pytest tests/contract
python -m compileall src
```

What these validations do not prove:

1. Desktop integration readiness
2. Installer correctness
3. Real provider runtime behavior
4. Persistent storage migration correctness
5. Production performance or reliability
6. HTTP transport hardening under load or failure conditions

## Windows Deployment Target

Target deployment rules are defined, but only partially implemented.

Expected target layout:

1. Install directory: application binaries and bundled sidecar runtime, read-only after install
2. `%APPDATA%`: configuration
3. `%LOCALAPPDATA%`: logs, cache, indexes, downloads, models, and mutable runtime assets

Current implementation progress:

1. Runtime path helpers now resolve config and local-data roots.
2. MRAG now persists manifests, source documents, and chunk indexes under the local runtime tree.

Not yet implemented end to end:

1. Model manifest and checksum workflow
2. Atomic download promotion
3. Production-grade MRAG storage layout
4. Desktop-to-sidecar production transport hardening
5. Production installer workflow

## Operational Readiness Boundary

The repository can currently support:

1. Architecture review
2. Contract-level development
3. Internal engineering validation of skeleton flows

The repository cannot yet support:

1. Production release to end users
2. Operational on-call ownership for a desktop product
3. Durable customer data handling
4. Stable runtime dependency packaging

## Release Gate Recommendation

Use the current repository as one of the following:

1. Architecture baseline
2. Contract-validation build
3. Internal engineering preview

Do not label the current repository as a production release until the following are complete:

1. Production-grade sidecar transport
2. Real LLM runtime execution
3. Production-grade persistent MRAG
4. Asset and artifact subsystems
5. Electron shell integration
6. Integration, packaging, and release validation suites

## Related Documents

- `docs/architecture/PycHermesAgent_Solution_Architecture_v0.2.0.md`
- `docs/architecture/Phase1_Roadmap_v0.2.0.md`
- `docs/design/PycHermesAgent_Detailed_Design_v0.2.0.md`
- `docs/features/PycHermesAgent_Feature_Details_v0.2.0.md`
