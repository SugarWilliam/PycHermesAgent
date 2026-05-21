# Phase 3 P0 Foundation Calibration Implementation Plan

> Historical implementation plan. Keep this document as the P0 execution record; use current contract and release-gate documents for the present repository baseline.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize the shared Phase 3 foundation by eliminating desktop-sidecar contract drift, freezing the first practical evidence schema, preserving PDF provenance, making the active JSON-backed MRAG runtime explicit, and fixing packaging gate drift.

**Architecture:** This plan intentionally limits scope to `P0` from `docs/superpowers/specs/2026-05-20-phase3-rollout-design.md`. The work updates contracts first, then aligns desktop consumers, then repairs evidence/provenance flow, then makes the current runtime/storage and packaging reality explicit. The plan avoids broad refactors and avoids starting `3A`, `3B`, `3E`, or `3F` feature work early.

**Tech Stack:** Python 3.11+, dataclass contracts, stdlib HTTP server, Electron, React 18, Zustand, pytest

---

## File Structure And Responsibilities

### Desktop runtime and protocol consumers

- `desktop/src/services/sidecarClient.js`
  Desktop HTTP/SSE client. Must match real sidecar routes and event names.
- `desktop/src/store/chatStore.js`
  Consumes streamed events and updates conversation state.
- `desktop/src/store/skillStore.js`
  Consumes `/skills` response shape and toggles activation state.
- `desktop/src/components/skills/SkillPanel.jsx`
  Reads normalized skill entries.
- `desktop/src/components/skills/SkillCard.jsx`
  Renders per-skill metadata and toggles activation.
- `desktop/src/components/context/CitationList.jsx`
  Renders the first richer citation fields from the frozen P0 evidence schema.
- `desktop/electron/main.js`
  Desktop-side view of sidecar URL and health probing.
- `desktop/package.json`
  Desktop packaging and CI commands must align with release gates.
- `desktop/README.md`
  Must document real build commands after package script alignment.

### Sidecar routes and service surfaces

- `src/pyc_hermes_agent/sidecar_api/http_server.py`
  Canonical route surface and SSE transport.
- `src/pyc_hermes_agent/sidecar_api/services/chat_service.py`
  Agent-loop orchestration surface for HTTP/SSE consumers.
- `src/pyc_hermes_agent/sidecar_api/services/skill_service.py`
  Sidecar-facing skill inventory and activation bridge.
- `src/pyc_hermes_agent/sidecar_api/services/mrag_service.py`
  Sidecar-facing MRAG ingest/search bridge. Current PDF provenance loss starts here.
- `src/pyc_hermes_agent/sidecar_api/services/common.py`
  Shared health/config snapshot helpers; good place to expose current MRAG runtime metadata without implying backend convergence that has not happened yet.
- `src/pyc_hermes_agent/sidecar_api/health.py`
  Health state payload for desktop/runtime visibility.

### Contracts and MRAG evidence path

- `src/pyc_hermes_agent/contracts/schemas.py`
  Source of truth for `Citation`, `DocumentChunk`, `KnowledgeDocument`, and retrieval payload fields.
- `src/pyc_hermes_agent/mrag_core/parse.py`
  Current document parsing baseline.
- `src/pyc_hermes_agent/mrag_core/chunk.py`
  Current chunk metadata generation. Needs frozen evidence/source-anchor fields.
- `src/pyc_hermes_agent/mrag_core/service.py`
  Current JSON-backed MRAG runtime service. P0 should clarify current runtime truth, not replace it with the future SQLite path.
- `src/pyc_hermes_agent/mrag_core/retrieve.py`
  Builds `Citation` objects from hits. Must propagate the frozen schema.
- `src/pyc_hermes_agent/mrag_core/pdf_extractor.py`
  Already has page metadata. P0 must stop dropping it later in the ingest flow.

### Release and documentation surfaces

- `scripts/release_gates.py`
  Current production gate script; currently drifts from desktop package scripts and docs.
- `docs/deployment/Production_Release_Gates.md`
  Must agree with actual gate commands.
- `docs/superpowers/plans/2026-05-20-phase3-p0-foundation-calibration.md`
  This plan file; keep in sync if task scope changes while planning.
- `docs/Documentation_Tracking.md`
  Update when docs change during this work.
- `docs/architecture/Compatibility_Matrix.md`
  Update if contract-visible fields change in a way the matrix tracks.

### Test surfaces

- `tests/contract/test_sidecar_http.py`
  Best place to lock route behavior, SSE event names, and sidecar HTTP payload shape.
- `tests/contract/test_sidecar_api.py`
  In-process sidecar service behavior.
- `tests/contract/test_sidecar_client.py`
  Python client and stream event expectations.
- `tests/contract/test_mrag_core.py`
  Retrieval citations and provenance.
- `tests/contract/test_pdf_extraction.py`
  PDF extraction chunk metadata expectations.
- `tests/contract/test_windows_packaging.py`
  Packaging policy and install immutability.

## Task 1: Align Sidecar Routes And SSE Event Contracts

**Files:**
- Modify: `desktop/src/services/sidecarClient.js`
- Modify: `desktop/src/store/chatStore.js`
- Modify: `desktop/electron/main.js`
- Test: `tests/contract/test_sidecar_http.py`
- Test: `tests/contract/test_sidecar_client.py`

- [ ] **Step 1: Write the failing contract tests for route and SSE alignment**

Add or update assertions in `tests/contract/test_sidecar_http.py` and `tests/contract/test_sidecar_client.py` so they lock the current canonical route and event names used by real server code.

```python
def test_sidecar_http_server_runs_formal_analysis(tmp_path) -> None:
    server, thread = _start_server(root=tmp_path)
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        status_code, payload = _post_json(
            f"{base_url}/formal-analysis",
            {
                "problem_statement": "network pagerank analysis",
                "data": {"adjacency": [[0.0, 1.0], [1.0, 0.0]]},
                "params": {"analysis": "pagerank"},
            },
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert status_code == 200
    assert payload["analysis"]["selected_method"] == "A-22"


def test_sidecar_http_stream_uses_real_agent_loop_event_names(tmp_path, monkeypatch) -> None:
    from pyc_hermes_agent.sidecar_api.services import chat_service as _chat_svc

    class _FakeAgentLoop:
        def __init__(self, *, root=None):
            self.root = root

        def stream(self, request, **kwargs):
            from pyc_hermes_agent.contracts import AgentLoopEvent, AgentLoopResult

            yield AgentLoopEvent(event="start", trace_id="trace-1", sequence=1, session_id="s1", model=request.model)
            yield AgentLoopEvent(
                event="assistant.tool_call.delta",
                trace_id="trace-1",
                sequence=2,
                session_id="s1",
                model=request.model,
                tool_calls=[{"id": "call-1", "name": "echo_text", "arguments": '{"text":"he'}],
            )
            yield AgentLoopEvent(
                event="assistant.delta",
                trace_id="trace-1",
                sequence=3,
                session_id="s1",
                model=request.model,
                delta="Hello",
            )
            yield AgentLoopEvent(
                event="done",
                trace_id="trace-1",
                sequence=4,
                is_terminal=True,
                session_id="s1",
                model=request.model,
                content="Hello",
                payload={"result": AgentLoopResult(session_id="s1", model=request.model, content="Hello")},
            )

    monkeypatch.setattr(_chat_svc, "AgentLoop", _FakeAgentLoop)
    server, thread = _start_server(root=tmp_path)
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        status_code, events = _post_sse(
            f"{base_url}/agent/run/stream",
            {
                "session_id": "s1",
                "model": "openai-compatible/demo-model",
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert status_code == 200
    assert [event["event"] for event in events] == [
        "start",
        "assistant.tool_call.delta",
        "assistant.delta",
        "done",
    ]
```

- [ ] **Step 2: Run the targeted tests to confirm current drift**

Run: `python -m pytest tests/contract/test_sidecar_http.py tests/contract/test_sidecar_client.py -q`
Expected: at least one failure around desktop-assumed route names or SSE event-name expectations once the new assertions are in place.

- [ ] **Step 3: Update the desktop client to use canonical routes and event names**

Modify `desktop/src/services/sidecarClient.js` so it calls `/formal-analysis`, recognizes `assistant.delta`, `assistant.tool_call.delta`, `tool.result`, and only emits one final done callback.

```javascript
export function streamAgent(request, handlers = {}) {
  const controller = new AbortController()

  ;(async () => {
    let sawDone = false
    try {
      const res = await fetch(`${getBaseUrl()}/agent/run/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
        signal: controller.signal
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: res.statusText }))
        handlers.onError?.(new Error(err.error?.message || err.message || `Stream failed: ${res.status}`), err)
        return
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const json = line.slice(6)
          if (!json.trim()) continue

          let event
          try {
            event = JSON.parse(json)
          } catch {
            continue
          }

          switch (event.event) {
            case 'start':
              handlers.onStart?.(event)
              break
            case 'assistant.delta':
              handlers.onDelta?.(event)
              break
            case 'assistant.tool_call.delta':
              handlers.onToolCall?.(event)
              break
            case 'tool.result':
              handlers.onToolResult?.(event)
              break
            case 'done':
              sawDone = true
              handlers.onDone?.(event)
              break
            case 'error':
              handlers.onError?.(new Error(event.error?.message || 'Stream error'), event)
              break
            default:
              handlers.onEvent?.(event)
          }
        }
      }

      if (!sawDone) {
        handlers.onDone?.({ event: 'done', finish_reason: 'stream_closed' })
      }
    } catch (err) {
      if (err.name !== 'AbortError') handlers.onError?.(err)
    }
  })()

  return controller
}

export async function runFormalAnalysis(request) {
  const res = await fetch(`${getBaseUrl()}/formal-analysis`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }))
    throw new Error(err.error?.message || err.message || `Analysis failed: ${res.status}`)
  }
  return res.json()
}
```

- [ ] **Step 4: Update the chat store to consume canonical stream events**

Modify `desktop/src/store/chatStore.js` so it reads `assistant.delta`, preserves tool-call deltas, and avoids stale done handling.

```javascript
import { create } from 'zustand'
import { streamAgent } from '../services/sidecarClient'

const useChatStore = create((set, get) => ({
  // existing state omitted

  sendMessage: (text, analysisMode = 'casual') => {
    const state = get()
    if (state.isStreaming) return

    let convId = state.activeConversationId
    if (!convId) convId = get().createConversation()

    get().addMessage(convId, { role: 'user', content: text, analysisMode })
    get().addMessage(convId, {
      role: 'assistant',
      content: '',
      toolCalls: [],
      traceId: null,
      model: null,
    })

    set({ isStreaming: true })

    const messages = get()
      .conversations.find((c) => c.id === convId)
      ?.messages
      .filter((m) => m.role === 'user' || m.role === 'assistant')
      .map((m) => ({ role: m.role, content: m.content })) || []

    const request = {
      messages,
      analysis_mode: analysisMode,
      planning_enabled: analysisMode !== 'casual',
      max_iterations: analysisMode === 'formal' ? 12 : 8,
    }

    const controller = streamAgent(request, {
      onStart: (event) => {
        get().updateLastAssistantMeta(convId, {
          traceId: event.trace_id,
          model: event.model,
          sessionId: event.session_id,
        })
      },
      onDelta: (event) => {
        if (event.delta) get().appendDelta(convId, event.delta)
      },
      onToolCall: (event) => {
        const calls = event.tool_calls || []
        get().updateLastAssistantMeta(convId, {
          toolCalls: calls.map((tc) => ({
            id: tc.id,
            name: tc.function?.name || tc.name,
            arguments: tc.function?.arguments || tc.arguments,
          })),
        })
      },
      onDone: (event) => {
        get().updateLastAssistantMeta(convId, {
          finishReason: event.finish_reason || 'stop',
          analysisCard: event.payload?.analysis_card || event.analysis_card,
        })
        set({ isStreaming: false, streamController: null })
      },
      onError: (err) => {
        get().appendDelta(convId, `\n\n**Error:** ${err.message}`)
        set({ isStreaming: false, streamController: null })
      },
    })

    set({ streamController: controller })
  },
}))
```

- [ ] **Step 5: Make Electron health probing reuse the same canonical sidecar route assumptions**

Modify `desktop/electron/main.js` so it keeps using `/health` but returns structured probe payloads that the renderer can surface later.

```javascript
function checkSidecarHealth() {
  return new Promise((resolve) => {
    const url = new URL('/health', SIDECAR_URL)
    const req = http.get(url, (res) => {
      let body = ''
      res.on('data', (chunk) => { body += chunk })
      res.on('end', () => {
        let parsed = null
        try {
          parsed = JSON.parse(body)
        } catch {
          parsed = null
        }
        resolve({
          ok: res.statusCode === 200,
          status: res.statusCode,
          url: SIDECAR_URL,
          payload: parsed,
          rawBody: parsed ? undefined : body,
        })
      })
    })
    req.on('error', (err) => resolve({ ok: false, status: 0, url: SIDECAR_URL, error: err.message }))
    req.setTimeout(3000, () => {
      req.destroy()
      resolve({ ok: false, status: 0, url: SIDECAR_URL, error: 'timeout' })
    })
  })
}
```

- [ ] **Step 6: Run the targeted tests to verify the contracts now match**

Run: `python -m pytest tests/contract/test_sidecar_http.py tests/contract/test_sidecar_client.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add desktop/src/services/sidecarClient.js desktop/src/store/chatStore.js desktop/electron/main.js tests/contract/test_sidecar_http.py tests/contract/test_sidecar_client.py
git commit -m "fix: align desktop and sidecar stream contracts"
```

## Task 2: Normalize Skill Inventory Payloads Across Sidecar And Desktop

This task and the remaining tasks follow the approved root plan in the shared workspace. Execute them in this worktree exactly as documented there.
