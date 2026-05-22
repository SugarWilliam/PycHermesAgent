# PycHermesAgent Desktop

React + Electron desktop shell for PycHermesAgent, built with electron-vite.

## Development

```bash
npm install
npm run dev
```

## Build

```bash
npm run build
npm run dist:dir             # unpacked for current OS (Ubuntu CI → linux-unpacked)
npm run dist:win-unpacked    # Windows unpacked — run on Windows; needs desktop/build/icon.ico
npm run dist                 # installer / platform defaults from electron-builder
```

## Sidecar Startup Contract

**Single authoritative policy:** URL resolution and launch decisions are owned by the **Electron main process** (`electron/sidecarRuntime.js`). The renderer must not invent a competing base URL; it uses **`window.sidecar.getRuntimeConfig()`** / **`sidecarClient.js`** (`resolved_url`).

### Resolved URL precedence (high → low)

Same order as implemented in `resolveSidecarRuntimeConfig()`:

| Order | Source | Settings panel label (**URL Source**) |
| ---: | --- | --- |
| 1 | `PYC_HERMES_SIDECAR_URL` | `env` |
| 2 | First line of `<userData>/sidecar_url.txt` | `file` |
| 3 | `sidecar_url` from `<userData>/sidecar-config.json` (written by Settings) | `desktop_config` |
| 4 | Default | `default` (`http://127.0.0.1:8765`) |

### Launch command precedence (high → low)

| Order | Source | Settings panel label (**Launch Source**) |
| ---: | --- | --- |
| 1 | `PYC_HERMES_SIDECAR_CMD` (parsed as a command line → argv) | `env` |
| 2 | `sidecar_command` / `sidecar_args` from `sidecar-config.json` | `desktop_config` |
| 3 | No launch command | `none` |

### Runtime behavior

- **Attach first:** probe `GET /health` on `resolved_url` before any spawn.
- If attach fails and a launch command exists, main spawns it and retries `/health` (bounded retries; see `sidecarRuntime.js`).
- **Saving Settings** persists `sidecar-config.json` then calls **`refreshSidecarRuntime({ allowLaunch: true })`** so a newly configured launch command can start the managed sidecar immediately (no extra “restart” step).
- **`sidecar:restart` / `window.sidecar.restart()`** forces the same attach-first startup path again (e.g. after external failures).

### Health and degraded UX (renderer)

- `SidecarStatusBanner` polls **`getStatus()`** + **`checkHealth()`** (`/health` payload: `status_label`, `state`, `degradation_reasons`). Chinese banner copy reflects startup errors, probe failures, and degraded / ready-with-warnings states.
- **Context panel — Sidecar runtime:** summarizes **Base URL**, **startup state** (attach vs launching vs unreachable), **`/health` aggregate** (`status_label` / `state` when reachable), and optional **raw JSON** for `runtimeStatus` plus the IPC health probe envelope (supports Phase 3A A2 diagnostics).
- **IPC:** `sidecar:url`, `getRuntimeConfig`, `setRuntimeConfig`, `getStatus`, `checkHealth`, `restart`.

### Overrides vs Settings

Environment variables and `sidecar_url.txt` **override** values shown in Settings; the panel displays **effective** resolved URL/source from main after IPC load.

## Chat streaming (SSE)

The renderer consumes `/agent/run/stream` (`sidecarClient.streamAgent`). Event types from the Hermes `AgentLoop` include at least: `start`, `plan`, `assistant.delta`, `assistant.tool_call.delta`, `assistant.completed`, `tool.result`, `retry`, `done`, `error`. **Stop** cancels via `AbortController`; the client invokes **`onAbort`** so **`isStreaming` clears** without a stuck spinner. Formal-mode **`analysis_card`** is attached on the terminal `done` event when present and is mirrored into the **Context panel** snapshot for Method / Evidence / SR / Risks / Assumptions (without forcing the panel open).

The request body includes **`activated_skills`** (names of toggled-on **builtin** skills from the sidebar), matching the sidecar `AgentLoopRequest` contract. Project-scoped skills listed from `/skills` remain **metadata-only** in the UI (not activatable via POST) per server policy.

## Sidecar services in the shell (Phase 3A A4)

- **Skills:** `GET /skills` → builtins (activatable) + project `items`; failures surface in the Skills panel (`lastFetchError`).
- **Preferences:** `GET /preferences` loads into **Context → Sidecar runtime** (read-only snapshot; use **Refresh probes & preferences**).
- **Citations:** `CitationList` is fed from **`tool.result` payloads** when the JSON body includes `citations` (or `retrieval.citations` / `result.citations`). Citations reset when the user sends a new message.

## Architecture

- `electron/main.js` — Electron main process, sidecar health probe
- `electron/preload.js` — contextBridge IPC exposure
- `src/` — React renderer (Vite + Tailwind)
- `electron.vite.config.js` — electron-vite build configuration
