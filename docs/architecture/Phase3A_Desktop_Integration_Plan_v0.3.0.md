# Phase 3A - Desktop Integration Plan v0.3.0

**Status:** Proposed execution plan
**Authority:** `docs/Project_Development_and_Release_Governance.md`
**Parent roadmap:** `docs/architecture/Phase3_Phase4_Productization_Roadmap_v0.3.0.md`
**Goal:** Convert the current desktop preview into a real Windows desktop shell that can start, connect to, supervise, and clearly diagnose the Python sidecar in normal local usage.

---

## 1. Scope

Phase 3A focuses on the runtime seam between the Electron desktop and the Python sidecar. This work does not add new analysis features. It makes the existing product path real, diagnosable, and packaging-ready.

In scope:

- Desktop-side sidecar startup and attach behavior
- Sidecar URL / port / path policy unification
- Clear degraded-state and unavailable-state UX
- Real SSE chat and health validation against the actual sidecar
- Packaging smoke for desktop + sidecar coexistence
- Runtime-path policy checks for installed desktop usage

Out of scope:

- Real-time network search
- New MRAG formats
- PPT/XLSX generation
- New MetaHarness methods

---

## 2. Current Baseline

Current completed baseline includes:

- `desktop/electron/main.js` health probes the sidecar at a default URL.
- `desktop/electron/preload.js` exposes `window.sidecar` and `window.updater` bridges.
- `desktop/src/services/sidecarClient.js` calls `/health`, `/agent/run`, `/agent/run/stream`, `/skills`, and `/meta/analyze`.
- `src/pyc_hermes_agent/sidecar_api/http_server.py` exposes the real sidecar routes, including `/health`, `/agent/run`, `/agent/run/stream`, `/skills`, `/assets`, `/artifacts`, and MRAG routes.
- Electron build was validated locally after fixing sidecar port drift and bundling issues in `desktop/electron/main.js`.

Key remaining gap:

- Desktop startup and sidecar interaction are still preview-grade and not yet a fully managed Windows runtime contract.

---

## 3. Architecture Rules

- Desktop may supervise sidecar lifecycle, but it must not bypass sidecar contracts to mutate MRAG, assets, artifacts, or analysis state.
- Runtime path ownership stays in Python-side policy code.
- The install directory remains read-only.
- Desktop configuration may live in user settings, but authoritative runtime write-path decisions must remain compatible with Python path policy.
- Sidecar health failure must degrade the desktop experience gracefully instead of failing silently.

---

## 4. Workstreams

### A1. Sidecar Startup Contract

**Goal:** define how the desktop finds, launches, and monitors the sidecar.

Target files:

- `desktop/electron/main.js`
- `desktop/electron/preload.js`
- `desktop/src/services/sidecarClient.js`
- `desktop/src/components/settings/SettingsPanel.jsx`
- `desktop/src/store/settingsStore.js`
- `desktop/README.md`

Required outcomes:

- One authoritative sidecar URL policy for dev and packaged runtime.
- Explicit precedence order for sidecar location resolution.
- Desktop can either attach to an already-running sidecar or launch a configured sidecar command.
- Launch failures become structured UI-visible states.

Acceptance:

- Desktop reaches usable chat UI when sidecar is already available.
- Desktop can surface a clear startup error when sidecar launch fails.
- No hidden mismatch between `main.js`, `sidecarClient.js`, and settings defaults.

### A2. Health and Degraded-State UX

**Goal:** make the desktop operationally understandable when the sidecar is unavailable or degraded.

Target files:

- `desktop/src/components/layout/AppLayout.jsx`
- `desktop/src/components/layout/ContextPanel.jsx`
- `desktop/src/components/settings/SettingsPanel.jsx`
- `desktop/src/store/uiStore.js`
- `desktop/src/services/sidecarClient.js`
- `src/pyc_hermes_agent/sidecar_api/health.py`

Required outcomes:

- Health state is visible early during app startup.
- States include at least: checking, ready, ready with warnings, degraded, unavailable.
- Desktop distinguishes connection failure from sidecar error response.
- Health probe details can be inspected from the UI.

Acceptance:

- A disconnected sidecar does not yield a blank or misleading UI.
- Degraded health from `/health` is shown as warnings, not success.

### A3. Real SSE and Chat Runtime Validation

**Goal:** ensure the desktop talks to the real sidecar event stream, not only a mock server.

Target files:

- `desktop/src/services/sidecarClient.js`
- `desktop/src/store/chatStore.js`
- `desktop/src/components/chat/ChatPanel.jsx`
- `desktop/src/components/chat/MessageList.jsx`
- `desktop/src/components/chat/MessageBubble.jsx`
- `desktop/src/components/chat/AnalysisCard.jsx`
- `src/pyc_hermes_agent/sidecar_api/http_server.py`
- `src/pyc_hermes_agent/sidecar_api/services/chat_service.py`

Required outcomes:

- Real `/agent/run/stream` event payloads render correctly.
- `start`, `delta`, `tool_call`, `done`, and `error` paths are all handled.
- Stop/cancel behavior works without leaving the UI in a stuck streaming state.
- Formal mode continues to display analysis cards.

Acceptance:

- Real SSE stream completes normally against the Python sidecar.
- Cancel stops the stream and returns UI control.
- Formal mode still attaches analysis-card metadata.

### A4. Sidecar Runtime Services in Desktop UX

**Goal:** expose already-implemented sidecar surfaces coherently in the desktop.

Target files:

- `desktop/src/components/layout/ContextPanel.jsx`
- `desktop/src/components/context/CitationList.jsx`
- `desktop/src/components/skills/SkillPanel.jsx`
- `desktop/src/components/settings/SettingsPanel.jsx`
- `desktop/src/store/skillStore.js`
- `desktop/src/store/citationStore.js`
- `desktop/src/services/sidecarClient.js`

Required outcomes:

- Skills listing and activation reflect the real sidecar response.
- Preferences and health are surfaced through the desktop instead of local assumptions.
- Citation panel remains consistent with real sidecar payloads.

Acceptance:

- Desktop skill toggles work against real `/skills` endpoints.
- Preferences and health no longer depend on mock-only assumptions.

### A5. Packaging and Install Validation

**Goal:** validate that the desktop and sidecar can coexist in a packaged Windows flow.

Target files:

- `desktop/package.json`
- `packaging/windows/*`
- `tests/contract/test_windows_packaging.py`
- `tests/contract/test_runtime_paths.py`
- `scripts/release_gates.py`
- `docs/deployment/*`

Required outcomes:

- `electron-builder --dir` and NSIS packaging remain green.
- Packaged runtime does not write mutable data under install directory.
- Sidecar startup assumptions are documented for packaged mode.

Acceptance:

- Packaging smoke passes locally.
- Runtime path rules remain compliant after install.

---

## 5. Execution Order

Recommended order:

1. A1 - Sidecar Startup Contract
2. A2 - Health and Degraded-State UX
3. A3 - Real SSE and Chat Runtime Validation
4. A4 - Sidecar Runtime Services in Desktop UX
5. A5 - Packaging and Install Validation

Rationale:

- Startup policy must be stable before UX and validation layers are trustworthy.
- Health UX must exist before packaging, otherwise packaged failure states are opaque.

---

## 6. Test Plan

Required verification:

- `npx electron-vite build` under `desktop/`
- real local sidecar `/health` smoke
- real `/agent/run/stream` smoke
- contract tests touching desktop packaging and runtime paths
- install smoke on a clean Windows environment before Phase 3A is declared complete

Target test areas:

- `tests/contract/test_windows_packaging.py`
- `tests/contract/test_runtime_paths.py`
- `tests/integration/test_sidecar_integration.py`

---

## 7. Risks

| Risk | Impact | Control |
|------|--------|---------|
| Desktop and sidecar ports drift again | Runtime connection failure | Single shared configuration source |
| Desktop silently falls back to wrong URL | False-positive startup | Explicit startup diagnostics and visible current sidecar URL |
| Packaged runtime writes to install dir | Packaging policy violation | Runtime path tests + packaging smoke |
| SSE stream shape drift breaks desktop | Broken chat UI | Contract checks for event payload compatibility |

---

## 8. Exit Definition

Phase 3A is complete when:

- Desktop can attach to or launch the real sidecar reliably.
- Health failures are visible and actionable in the UI.
- Real SSE chat works end-to-end without a mock server.
- Packaging smoke is green for the desktop shell.
- Runtime path policy remains Windows-compliant in packaged mode.

---
