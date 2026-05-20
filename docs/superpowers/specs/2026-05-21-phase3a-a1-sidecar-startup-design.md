# Phase 3A A1 Sidecar Startup Contract Design

**Date:** 2026-05-21
**Status:** Proposed design
**Scope:** Phase 3A / A1 sidecar startup contract for the Electron desktop shell
**Primary references:**
- `docs/architecture/Phase3_Phase4_Productization_Roadmap_v0.3.0.md`
- `docs/architecture/Phase3A_Desktop_Integration_Plan_v0.3.0.md`
- `docs/architecture/Phase1_Roadmap_v0.2.0.md`
- `docs/constraints/windows-packaging.md`

## 1. Goal

Define one authoritative desktop-sidecar startup contract so the Electron desktop can reliably attach to an already-running sidecar or, when explicitly configured, launch one and report structured startup state.

This design is intentionally narrower than Phase 3A as a whole. It only covers `A1. Sidecar Startup Contract` and leaves health UX, SSE/runtime UX, and packaging validation to later Phase 3A work.

## 2. Current Baseline

The current repository already has a working preview desktop and a real Python sidecar, but the startup contract is split across incompatible sources:

- `desktop/electron/main.js` resolves the sidecar URL from `PYC_HERMES_SIDECAR_URL` or a hardcoded default only.
- `desktop/src/services/sidecarClient.js` resolves the base URL from renderer-side state (`settingsStore.sidecarUrl`) or a default.
- `desktop/src/store/settingsStore.js` persists `sidecarUrl` in renderer `localStorage`.
- `desktop/src/components/settings/SettingsPanel.jsx` edits that renderer-owned `sidecarUrl` directly.
- There is no structured attach-vs-launch contract and no desktop-owned persisted launch configuration.

This means the main process and renderer can disagree about which sidecar URL is active, which makes reliable attach-first startup impossible.

## 3. Decisions

### 3.1 Main-process authority

The Electron main process becomes the only authority for sidecar runtime configuration and startup state.

- Renderer code does not decide the effective sidecar URL.
- Renderer code does not persist sidecar startup settings in `localStorage`.
- Settings UI reads and writes sidecar startup settings through IPC.
- Non-sidecar UI settings such as `theme`, `defaultModel`, and `defaultAnalysisMode` stay in the existing renderer store for now.

### 3.2 Attach first, opt-in launch

Desktop startup follows this rule:

1. Resolve the effective sidecar URL and launch configuration.
2. Probe `/health` at the resolved URL.
3. If the probe succeeds, attach and do not launch anything.
4. If the probe fails and no launch command is configured, report `unavailable`.
5. If the probe fails and a launch command is configured, launch the sidecar, retry health for a bounded interval, and report either `launched` or `launch_failed`.

This keeps the desktop compatible with user-managed sidecars while still enabling desktop-managed startup when the user explicitly configures it.

### 3.3 URL precedence

The effective sidecar URL resolves in this order:

1. `PYC_HERMES_SIDECAR_URL`
2. `sidecar_url.txt`
3. Desktop-owned persisted sidecar config
4. Default `http://127.0.0.1:8765`

This preserves the Phase 1 preview contract recorded in repo docs while adding a desktop-owned configuration layer underneath env/file overrides.

### 3.4 Launch command precedence

The effective launch command resolves in this order:

1. `PYC_HERMES_SIDECAR_CMD`
2. Desktop-owned persisted sidecar config
3. No launch command

When the effective launch command comes from the environment, it remains an override and the desktop settings UI reports that a higher-priority source is active.

### 3.5 Compatibility file role

`sidecar_url.txt` remains a compatibility input only.

- The main process reads it.
- The settings UI does not write it.
- The settings UI writes the desktop-owned JSON config instead.
- If `sidecar_url.txt` is currently winning, the UI shows that the active URL source is `file` so the override is visible.

This avoids maintaining two writable desktop configuration surfaces for the same value.

## 4. Runtime Configuration Model

All desktop-owned mutable startup configuration lives under Electron `app.getPath("userData")`, not under the install directory.

Files:

- Desktop-owned startup config: `<userData>/sidecar-config.json`
- Compatibility URL override file: `<userData>/sidecar_url.txt`

Suggested JSON shape:

```json
{
  "sidecar_url": "http://127.0.0.1:8765",
  "sidecar_command": "pyc-hermes-sidecar",
  "sidecar_args": ["--host", "127.0.0.1", "--port", "8765"]
}
```

Rules:

- Persisted config stores command and args separately so the desktop can spawn without shell-dependent command parsing.
- `PYC_HERMES_SIDECAR_CMD` remains a compatibility override from the environment and may be parsed as a command-line string before `spawn(..., { shell: false })`.
- Timeouts and retry counts stay as code-level constants in `A1`; they are not user-facing settings yet.

## 5. Component Responsibilities

### 5.1 `desktop/electron/main.js`

Owns:

- loading desktop-owned sidecar config
- reading `sidecar_url.txt`
- resolving effective URL and launch command
- attach-first health probing
- optional sidecar launch
- structured startup status
- IPC handlers for renderer reads and writes

Tracks whether the current sidecar was launched by the desktop. The desktop may terminate only the child process that it started itself. It must not try to stop an externally managed sidecar that it merely attached to.

### 5.2 `desktop/electron/preload.js`

Exposes a sidecar API to the renderer, including:

- `getRuntimeConfig()`
- `setRuntimeConfig(partial)`
- `getStatus()`
- `checkHealth()`

Renderer code uses these IPC-backed methods instead of computing URL precedence locally.

### 5.3 `desktop/src/services/sidecarClient.js`

Stops reading `settingsStore.sidecarUrl`.

All HTTP and SSE requests use the resolved URL provided by the main process. The client becomes a transport consumer of the desktop startup contract rather than a second configuration authority.

### 5.4 `desktop/src/components/settings/SettingsPanel.jsx`

Shows and edits the desktop-owned sidecar config through IPC.

The sidecar settings area shows at least:

- current effective URL
- effective URL source: `env`, `file`, `desktop_config`, or `default`
- whether launch is configured
- launch command source: `env`, `desktop_config`, or `none`

When env or file overrides are active, the UI still allows editing desktop-owned defaults, but it must make it clear that those values are not currently winning.

### 5.5 `desktop/src/store/settingsStore.js`

Removes `sidecarUrl` from renderer-owned persistent settings.

Keeps renderer-only values that do not define the sidecar startup contract.

## 6. Startup and Status Flow

Startup flow:

1. Desktop starts.
2. Main process loads `sidecar-config.json` if present.
3. Main process reads `sidecar_url.txt` if present.
4. Main process resolves effective URL and launch command according to precedence.
5. Main process probes `/health` at the effective URL.
6. On probe success, status becomes `attached`.
7. On probe failure with no launch command, status becomes `unavailable`.
8. On probe failure with a launch command, status becomes `launching`, the sidecar is spawned, and bounded health retries begin.
9. On successful retry, status becomes `launched`.
10. On retry exhaustion or early child exit, status becomes `launch_failed`.

If a desktop-launched sidecar later exits, the main process records the failure in structured status, but `A1` does not add auto-restart behavior.

## 7. Status and Error Contract

Minimum `startup_state` values:

- `checking`
- `attached`
- `launching`
- `launched`
- `unavailable`
- `launch_failed`

Minimum status payload fields:

```json
{
  "startup_state": "attached",
  "resolved_url": "http://127.0.0.1:8765",
  "resolved_url_source": "desktop_config",
  "launch_configured": true,
  "launch_command_source": "desktop_config",
  "managed_process": false,
  "last_probe": null,
  "last_error": null
}
```

Minimum error codes:

- `attach_unreachable`
- `attach_http_error`
- `launch_not_configured`
- `launch_spawn_failed`
- `launch_probe_timeout`
- `launch_exited_early`

Each `last_error` entry contains:

- `code`
- `message`
- `stage`
- `details`

This gives Phase 3A / A2 enough structure to build degraded-state UI without redefining startup semantics.

## 8. Files In Scope

Implementation for `A1` is expected to touch at least:

- `desktop/electron/main.js`
- `desktop/electron/preload.js`
- `desktop/src/services/sidecarClient.js`
- `desktop/src/components/settings/SettingsPanel.jsx`
- `desktop/src/store/settingsStore.js`
- `desktop/README.md`

Documentation updates may also touch:

- `docs/Documentation_Tracking.md`
- `docs/architecture/Compatibility_Matrix.md` if IPC-visible payloads become contract-visible enough to merit matrix tracking

## 9. Verification

`A1` verification proves the startup contract rather than broader product behavior.

Required checks:

1. URL precedence works as designed:
   - env overrides file, config, and default
   - file overrides config and default
   - config overrides default when env/file are absent
2. Renderer no longer decides the effective sidecar URL from local settings.
3. Attach-first behavior works:
   - a healthy sidecar attaches without launching a child process
4. Opt-in launch works:
   - attach failure plus configured launch command can produce `launched`
5. Failure paths are structured:
   - missing launch command produces `unavailable`
   - bad launch command produces `launch_spawn_failed`
   - probe timeout after launch produces `launch_probe_timeout`
6. Desktop build still passes:
   - `npx electron-vite build`

To keep the startup contract testable without broad refactoring, implementation may extract command resolution and health-probe helpers into focused functions or a small helper module under `desktop/electron/`. Larger desktop architecture changes remain out of scope for `A1`.

## 10. Out Of Scope

This design does not include:

- full degraded-state UX (`A2`)
- full SSE/chat runtime validation (`A3`)
- packaged installer behavior beyond respecting writable config location rules
- sidecar auto-restart or watchdog behavior
- updater integration
- Python-side runtime path ownership changes

## 11. Acceptance

`Phase 3A / A1` is complete when:

- desktop and renderer share one authoritative sidecar URL truth through the main process
- desktop can attach to an already-running sidecar without spawning one unnecessarily
- desktop can launch a configured sidecar command after attach failure
- startup state and startup failures are exposed in a structured form that later UI work can consume
- mutable desktop startup config is stored outside the install directory
