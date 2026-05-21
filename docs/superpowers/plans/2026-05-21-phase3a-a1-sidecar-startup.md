# Phase 3A A1 Sidecar Startup Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Electron main process the single authority for sidecar URL resolution, startup policy, and structured startup state so the desktop can attach first and only launch a sidecar when explicitly configured.

**Architecture:** This plan implements the approved `docs/superpowers/specs/2026-05-21-phase3a-a1-sidecar-startup-design.md` without expanding into Phase 3A `A2` or `A3`. The work introduces one focused Electron helper for runtime config and attach/launch control, wires that helper into `main.js` and `preload.js`, migrates renderer-side consumers away from `localStorage` sidecar URL state, and then documents and verifies the final contract.

**Tech Stack:** Electron main/preload (CommonJS), React 18, Zustand, Node built-in test runner, pytest

---

## File Structure And Responsibilities

### Desktop startup authority

- `desktop/electron/sidecarRuntime.js`
  New helper module for desktop-owned sidecar config paths, persisted config I/O, precedence resolution, `/health` probing, attach-first startup, and structured startup status.
- `desktop/electron/sidecarRuntime.test.js`
  Node built-in tests for precedence resolution and attach/launch state transitions.
- `desktop/electron/main.js`
  Electron authority that owns the runtime controller, IPC handlers, initial startup attach/launch, and managed-child shutdown.
- `desktop/electron/preload.js`
  Exposes the main-process-owned sidecar runtime API to the renderer.

### Renderer consumers

- `desktop/src/services/sidecarClient.js`
  Uses main-process resolved sidecar URL for HTTP/SSE; stops reading renderer-owned `sidecarUrl`.
- `desktop/src/components/settings/SettingsPanel.jsx`
  Reads and writes desktop-owned sidecar settings over IPC and shows resolved source/status.
- `desktop/src/store/settingsStore.js`
  Keeps renderer-only UI preferences and drops the old persisted `sidecarUrl` field.

### Documentation and regression checks

- `desktop/README.md`
  Documents precedence, `attach first`, and opt-in launch behavior.
- `docs/Documentation_Tracking.md`
  Tracks the new plan document in the docs manifest.
- `tests/contract/test_sidecar_client.py`
  Static regression checks for desktop JS source files.
- `tests/contract/test_windows_packaging.py`
  Packaging/doc regression checks for startup-contract documentation.
- `tests/integration/test_sidecar_integration.py`
  Existing sidecar HTTP smoke coverage; used to ensure A1 does not disturb Python-side routes.

## Task 1: Create The Main-Process Sidecar Runtime Helper

**Files:**
- Create: `desktop/electron/sidecarRuntime.js`
- Create: `desktop/electron/sidecarRuntime.test.js`

- [ ] **Step 1: Write the failing Node tests for precedence and command parsing**

Create `desktop/electron/sidecarRuntime.test.js` with concrete expectations for env/file/config/default precedence and quoted command parsing.

```javascript
const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const os = require('node:os')
const { join } = require('node:path')

const {
  DEFAULT_SIDECAR_URL,
  splitCommandLine,
  resolveSidecarRuntimeConfig,
} = require('./sidecarRuntime')

test('splitCommandLine preserves quoted args', () => {
  assert.deepEqual(
    splitCommandLine('pyc-hermes-sidecar "--host=127.0.0.1" --port 8765'),
    ['pyc-hermes-sidecar', '--host=127.0.0.1', '--port', '8765']
  )
})

test('resolveSidecarRuntimeConfig prefers env over file and config', () => {
  const userDataDir = fs.mkdtempSync(join(os.tmpdir(), 'pyc-hermes-sidecar-'))
  fs.writeFileSync(
    join(userDataDir, 'sidecar-config.json'),
    JSON.stringify({
      sidecar_url: 'http://persisted:9000',
      sidecar_command: 'pyc-hermes-sidecar',
      sidecar_args: ['--port', '9000'],
    }),
    'utf8'
  )
  fs.writeFileSync(join(userDataDir, 'sidecar_url.txt'), 'http://file:9100\n', 'utf8')

  const runtime = resolveSidecarRuntimeConfig({
    env: {
      PYC_HERMES_SIDECAR_URL: 'http://env:9200',
      PYC_HERMES_SIDECAR_CMD: 'pyc-hermes-sidecar --port 9200',
    },
    userDataDir,
  })

  assert.equal(runtime.resolvedUrl, 'http://env:9200')
  assert.equal(runtime.resolvedUrlSource, 'env')
  assert.equal(runtime.launchCommand, 'pyc-hermes-sidecar')
  assert.deepEqual(runtime.launchArgs, ['--port', '9200'])
  assert.equal(runtime.launchCommandSource, 'env')
})

test('resolveSidecarRuntimeConfig falls back from file to config to default', () => {
  const userDataDir = fs.mkdtempSync(join(os.tmpdir(), 'pyc-hermes-sidecar-'))
  fs.writeFileSync(
    join(userDataDir, 'sidecar-config.json'),
    JSON.stringify({ sidecar_url: 'http://persisted:9000', sidecar_command: '', sidecar_args: [] }),
    'utf8'
  )
  fs.writeFileSync(join(userDataDir, 'sidecar_url.txt'), 'http://file:9100\n', 'utf8')

  const fileRuntime = resolveSidecarRuntimeConfig({ env: {}, userDataDir })
  assert.equal(fileRuntime.resolvedUrl, 'http://file:9100')
  assert.equal(fileRuntime.resolvedUrlSource, 'file')

  fs.unlinkSync(join(userDataDir, 'sidecar_url.txt'))
  const configRuntime = resolveSidecarRuntimeConfig({ env: {}, userDataDir })
  assert.equal(configRuntime.resolvedUrl, 'http://persisted:9000')
  assert.equal(configRuntime.resolvedUrlSource, 'desktop_config')

  fs.unlinkSync(join(userDataDir, 'sidecar-config.json'))
  const defaultRuntime = resolveSidecarRuntimeConfig({ env: {}, userDataDir })
  assert.equal(defaultRuntime.resolvedUrl, DEFAULT_SIDECAR_URL)
  assert.equal(defaultRuntime.resolvedUrlSource, 'default')
})
```

- [ ] **Step 2: Run the Node tests to verify the helper does not exist yet**

Run: `node --test desktop/electron/sidecarRuntime.test.js`
Expected: FAIL with `Cannot find module './sidecarRuntime'` or missing export failures.

- [ ] **Step 3: Create `desktop/electron/sidecarRuntime.js` with config paths, parsing, and precedence resolution**

Add the helper module with exact persisted-config behavior.

```javascript
const fs = require('node:fs')
const { join } = require('node:path')

const DEFAULT_SIDECAR_URL = 'http://127.0.0.1:8765'
const DEFAULT_ATTACH_TIMEOUT_MS = 3000
const DEFAULT_LAUNCH_RETRIES = 10
const DEFAULT_LAUNCH_RETRY_DELAY_MS = 500

function sidecarConfigPath(userDataDir) {
  return join(userDataDir, 'sidecar-config.json')
}

function sidecarUrlOverridePath(userDataDir) {
  return join(userDataDir, 'sidecar_url.txt')
}

function splitCommandLine(raw) {
  const value = String(raw || '').trim()
  const tokens = []
  let current = ''
  let quote = null

  for (const char of value) {
    if (quote) {
      if (char === quote) {
        quote = null
      } else {
        current += char
      }
      continue
    }

    if (char === '"' || char === "'") {
      quote = char
      continue
    }

    if (/\s/.test(char)) {
      if (current) {
        tokens.push(current)
        current = ''
      }
      continue
    }

    current += char
  }

  if (current) tokens.push(current)
  return tokens
}

function loadPersistedSidecarConfig(userDataDir, fsImpl = fs) {
  const filePath = sidecarConfigPath(userDataDir)
  if (!fsImpl.existsSync(filePath)) {
    return { sidecar_url: '', sidecar_command: '', sidecar_args: [] }
  }

  const raw = JSON.parse(fsImpl.readFileSync(filePath, 'utf8'))
  return {
    sidecar_url: typeof raw.sidecar_url === 'string' ? raw.sidecar_url.trim() : '',
    sidecar_command: typeof raw.sidecar_command === 'string' ? raw.sidecar_command.trim() : '',
    sidecar_args: Array.isArray(raw.sidecar_args) ? raw.sidecar_args.map((item) => String(item).trim()).filter(Boolean) : [],
  }
}

function savePersistedSidecarConfig(userDataDir, nextConfig, fsImpl = fs) {
  const sanitized = {
    sidecar_url: typeof nextConfig.sidecar_url === 'string' ? nextConfig.sidecar_url.trim() : '',
    sidecar_command: typeof nextConfig.sidecar_command === 'string' ? nextConfig.sidecar_command.trim() : '',
    sidecar_args: Array.isArray(nextConfig.sidecar_args) ? nextConfig.sidecar_args.map((item) => String(item).trim()).filter(Boolean) : [],
  }
  fsImpl.mkdirSync(userDataDir, { recursive: true })
  fsImpl.writeFileSync(sidecarConfigPath(userDataDir), JSON.stringify(sanitized, null, 2), 'utf8')
  return sanitized
}

function readSidecarUrlOverride(userDataDir, fsImpl = fs) {
  const filePath = sidecarUrlOverridePath(userDataDir)
  if (!fsImpl.existsSync(filePath)) return ''
  return fsImpl.readFileSync(filePath, 'utf8').trim()
}

function resolveSidecarRuntimeConfig({ env = process.env, userDataDir, fsImpl = fs } = {}) {
  const persisted = loadPersistedSidecarConfig(userDataDir, fsImpl)
  const fileUrl = readSidecarUrlOverride(userDataDir, fsImpl)
  const envUrl = String(env.PYC_HERMES_SIDECAR_URL || '').trim()
  const envCommandRaw = String(env.PYC_HERMES_SIDECAR_CMD || '').trim()
  const envCommand = splitCommandLine(envCommandRaw)

  const resolvedUrl = envUrl || fileUrl || persisted.sidecar_url || DEFAULT_SIDECAR_URL
  const resolvedUrlSource = envUrl ? 'env' : fileUrl ? 'file' : persisted.sidecar_url ? 'desktop_config' : 'default'
  const launchCommand = envCommand[0] || persisted.sidecar_command || ''
  const launchArgs = envCommand.length ? envCommand.slice(1) : persisted.sidecar_args
  const launchCommandSource = envCommand.length ? 'env' : persisted.sidecar_command ? 'desktop_config' : 'none'

  return {
    resolvedUrl,
    resolvedUrlSource,
    launchConfigured: Boolean(launchCommand),
    launchCommand,
    launchArgs,
    launchCommandSource,
    persistedConfig: persisted,
  }
}

module.exports = {
  DEFAULT_SIDECAR_URL,
  DEFAULT_ATTACH_TIMEOUT_MS,
  DEFAULT_LAUNCH_RETRIES,
  DEFAULT_LAUNCH_RETRY_DELAY_MS,
  sidecarConfigPath,
  sidecarUrlOverridePath,
  splitCommandLine,
  loadPersistedSidecarConfig,
  savePersistedSidecarConfig,
  readSidecarUrlOverride,
  resolveSidecarRuntimeConfig,
}
```

- [ ] **Step 4: Run the Node tests to verify precedence now passes**

Run: `node --test desktop/electron/sidecarRuntime.test.js`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add desktop/electron/sidecarRuntime.js desktop/electron/sidecarRuntime.test.js
git commit -m "feat: add desktop sidecar runtime config helper"
```

## Task 2: Wire Attach-First Startup And Main-Process IPC

**Files:**
- Modify: `desktop/electron/sidecarRuntime.js`
- Modify: `desktop/electron/sidecarRuntime.test.js`
- Modify: `desktop/electron/main.js`
- Modify: `desktop/electron/preload.js`

- [ ] **Step 1: Extend the Node tests to cover attach-before-launch, successful launch, and spawn failure**

Append these tests to `desktop/electron/sidecarRuntime.test.js`.

```javascript
const { EventEmitter } = require('node:events')
const { attachFirstStartup } = require('./sidecarRuntime')

test('attachFirstStartup attaches without spawning when probe succeeds', async () => {
  const runtime = {
    resolvedUrl: 'http://127.0.0.1:8765',
    resolvedUrlSource: 'default',
    launchConfigured: true,
    launchCommand: 'pyc-hermes-sidecar',
    launchArgs: ['--port', '8765'],
    launchCommandSource: 'desktop_config',
  }

  const result = await attachFirstStartup(runtime, {
    probeImpl: async () => ({ ok: true, status: 200, url: runtime.resolvedUrl, payload: { status_label: 'ready' } }),
    spawnImpl: () => { throw new Error('spawn should not run') },
    sleep: async () => {},
  })

  assert.equal(result.status.startup_state, 'attached')
  assert.equal(result.status.managed_process, false)
})

test('attachFirstStartup launches after attach failure and reaches launched', async () => {
  let attempts = 0
  let spawnCalls = 0
  const child = new EventEmitter()
  child.pid = 4321
  child.kill = () => {}

  const result = await attachFirstStartup(
    {
      resolvedUrl: 'http://127.0.0.1:8765',
      resolvedUrlSource: 'desktop_config',
      launchConfigured: true,
      launchCommand: 'pyc-hermes-sidecar',
      launchArgs: ['--port', '8765'],
      launchCommandSource: 'desktop_config',
    },
    {
      probeImpl: async () => {
        attempts += 1
        return attempts < 2
          ? { ok: false, status: 0, url: 'http://127.0.0.1:8765', error: 'ECONNREFUSED' }
          : { ok: true, status: 200, url: 'http://127.0.0.1:8765', payload: { status_label: 'ready' } }
      },
      spawnImpl: () => {
        spawnCalls += 1
        return child
      },
      sleep: async () => {},
      launchRetries: 2,
      launchRetryDelayMs: 0,
    }
  )

  assert.equal(spawnCalls, 1)
  assert.equal(result.status.startup_state, 'launched')
  assert.equal(result.status.managed_process, true)
})

test('attachFirstStartup reports launch_spawn_failed when spawn throws', async () => {
  const result = await attachFirstStartup(
    {
      resolvedUrl: 'http://127.0.0.1:8765',
      resolvedUrlSource: 'desktop_config',
      launchConfigured: true,
      launchCommand: 'pyc-hermes-sidecar',
      launchArgs: ['--port', '8765'],
      launchCommandSource: 'desktop_config',
    },
    {
      probeImpl: async () => ({ ok: false, status: 0, url: 'http://127.0.0.1:8765', error: 'ECONNREFUSED' }),
      spawnImpl: () => { throw new Error('missing executable') },
      sleep: async () => {},
    }
  )

  assert.equal(result.status.startup_state, 'launch_failed')
  assert.equal(result.status.last_error.code, 'launch_spawn_failed')
})
```

- [ ] **Step 2: Run the Node tests to verify the startup state machine is not implemented yet**

Run: `node --test desktop/electron/sidecarRuntime.test.js`
Expected: FAIL with missing `attachFirstStartup` export or missing startup-state fields.

- [ ] **Step 3: Implement the attach-first state machine and wire it into `main.js` and `preload.js`**

Update `desktop/electron/sidecarRuntime.js` first.

```javascript
const http = require('node:http')
const { spawn } = require('node:child_process')

function buildSidecarStatus(runtime) {
  return {
    startup_state: 'checking',
    resolvedUrl: runtime.resolvedUrl,
    resolvedUrlSource: runtime.resolvedUrlSource,
    launchConfigured: runtime.launchConfigured,
    launchCommandSource: runtime.launchCommandSource,
    managed_process: false,
    last_probe: null,
    last_error: null,
  }
}

function probeSidecarHealth(baseUrl, { httpGet = http.get, timeoutMs = DEFAULT_ATTACH_TIMEOUT_MS } = {}) {
  return new Promise((resolve) => {
    const url = new URL('/health', baseUrl)
    const req = httpGet(url, (res) => {
      let body = ''
      res.on('data', (chunk) => { body += chunk })
      res.on('end', () => {
        try {
          const payload = JSON.parse(body)
          resolve({ ok: res.statusCode === 200, status: res.statusCode, url: baseUrl, payload })
        } catch {
          resolve({ ok: false, status: res.statusCode, url: baseUrl, rawBody: body, error: 'invalid_json' })
        }
      })
    })
    req.on('error', (err) => resolve({ ok: false, status: 0, url: baseUrl, error: err.message }))
    req.setTimeout(timeoutMs, () => {
      req.destroy()
      resolve({ ok: false, status: 0, url: baseUrl, error: 'timeout' })
    })
  })
}

async function attachFirstStartup(runtime, deps = {}) {
  const probeImpl = deps.probeImpl || ((baseUrl) => probeSidecarHealth(baseUrl, deps))
  const spawnImpl = deps.spawnImpl || spawn
  const sleep = deps.sleep || ((ms) => new Promise((resolve) => setTimeout(resolve, ms)))
  const launchRetries = Number.isInteger(deps.launchRetries) ? deps.launchRetries : DEFAULT_LAUNCH_RETRIES
  const launchRetryDelayMs = Number.isInteger(deps.launchRetryDelayMs) ? deps.launchRetryDelayMs : DEFAULT_LAUNCH_RETRY_DELAY_MS
  const status = buildSidecarStatus(runtime)

  const firstProbe = await probeImpl(runtime.resolvedUrl)
  status.last_probe = firstProbe
  if (firstProbe.ok) {
    status.startup_state = 'attached'
    return { status, child: null }
  }

  if (!runtime.launchConfigured) {
    status.startup_state = 'unavailable'
    status.last_error = {
      code: 'launch_not_configured',
      message: 'Attach failed and no launch command is configured.',
      stage: 'attach',
      details: firstProbe,
    }
    return { status, child: null }
  }

  status.startup_state = 'launching'

  let child
  let earlyExit = null
  try {
    child = spawnImpl(runtime.launchCommand, runtime.launchArgs, { shell: false, stdio: 'ignore', windowsHide: true })
    child.once('exit', (code, signal) => {
      earlyExit = { code, signal }
    })
  } catch (error) {
    status.startup_state = 'launch_failed'
    status.last_error = {
      code: 'launch_spawn_failed',
      message: error.message,
      stage: 'launch',
      details: { command: runtime.launchCommand, args: runtime.launchArgs },
    }
    return { status, child: null }
  }

  for (let attempt = 0; attempt < launchRetries; attempt += 1) {
    await sleep(launchRetryDelayMs)
    const probe = await probeImpl(runtime.resolvedUrl)
    status.last_probe = probe

    if (probe.ok) {
      status.startup_state = 'launched'
      status.managed_process = true
      return { status, child }
    }

    if (earlyExit) {
      status.startup_state = 'launch_failed'
      status.last_error = {
        code: 'launch_exited_early',
        message: 'Sidecar process exited before health checks passed.',
        stage: 'launch',
        details: earlyExit,
      }
      return { status, child }
    }
  }

  status.startup_state = 'launch_failed'
  status.last_error = {
    code: 'launch_probe_timeout',
    message: 'Sidecar did not become healthy before retry budget was exhausted.',
    stage: 'launch',
    details: { retries: launchRetries, delay_ms: launchRetryDelayMs },
  }
  return { status, child }
}

module.exports = {
  DEFAULT_SIDECAR_URL,
  DEFAULT_ATTACH_TIMEOUT_MS,
  DEFAULT_LAUNCH_RETRIES,
  DEFAULT_LAUNCH_RETRY_DELAY_MS,
  sidecarConfigPath,
  sidecarUrlOverridePath,
  splitCommandLine,
  loadPersistedSidecarConfig,
  savePersistedSidecarConfig,
  readSidecarUrlOverride,
  resolveSidecarRuntimeConfig,
  buildSidecarStatus,
  probeSidecarHealth,
  attachFirstStartup,
}
```

Then wire `desktop/electron/main.js`.

```javascript
const { app, BrowserWindow, ipcMain } = require('electron')
const { join } = require('path')
const {
  buildSidecarStatus,
  loadPersistedSidecarConfig,
  savePersistedSidecarConfig,
  resolveSidecarRuntimeConfig,
  probeSidecarHealth,
  attachFirstStartup,
} = require('./sidecarRuntime')

let runtimeConfig = {
  resolvedUrl: 'http://127.0.0.1:8765',
  resolvedUrlSource: 'default',
  launchConfigured: false,
  launchCommand: '',
  launchArgs: [],
  launchCommandSource: 'none',
  persistedConfig: { sidecar_url: '', sidecar_command: '', sidecar_args: [] },
}
let runtimeStatus = buildSidecarStatus(runtimeConfig)
let managedSidecar = null

function stopManagedSidecar() {
  if (managedSidecar && !managedSidecar.killed) managedSidecar.kill()
  managedSidecar = null
}

async function refreshSidecarRuntime({ allowLaunch }) {
  runtimeConfig = resolveSidecarRuntimeConfig({ env: process.env, userDataDir: app.getPath('userData') })

  if (allowLaunch) {
    const result = await attachFirstStartup(runtimeConfig)
    runtimeStatus = result.status
    managedSidecar = result.status.managed_process ? result.child : null
    return runtimeStatus
  }

  const probe = await probeSidecarHealth(runtimeConfig.resolvedUrl)
  runtimeStatus = {
    ...buildSidecarStatus(runtimeConfig),
    startup_state: probe.ok ? 'attached' : 'unavailable',
    last_probe: probe,
    last_error: probe.ok
      ? null
      : {
          code: probe.status === 0 ? 'attach_unreachable' : 'attach_http_error',
          message: probe.error || `HTTP ${probe.status}`,
          stage: 'attach',
          details: probe,
        },
  }
  return runtimeStatus
}

ipcMain.handle('sidecar:get-runtime-config', async () => runtimeConfig)
ipcMain.handle('sidecar:get-status', async () => runtimeStatus)
ipcMain.handle('sidecar:check-health', async () => refreshSidecarRuntime({ allowLaunch: false }))
ipcMain.handle('sidecar:url', async () => runtimeConfig.resolvedUrl)
ipcMain.handle('sidecar:set-runtime-config', async (_event, partial) => {
  const current = loadPersistedSidecarConfig(app.getPath('userData'))
  const next = savePersistedSidecarConfig(app.getPath('userData'), {
    sidecar_url: typeof partial.sidecar_url === 'string' ? partial.sidecar_url : current.sidecar_url,
    sidecar_command: typeof partial.sidecar_command === 'string' ? partial.sidecar_command : current.sidecar_command,
    sidecar_args: Array.isArray(partial.sidecar_args) ? partial.sidecar_args : current.sidecar_args,
  })
  await refreshSidecarRuntime({ allowLaunch: false })
  return { ...runtimeConfig, persistedConfig: next }
})

app.whenReady().then(async () => {
  await refreshSidecarRuntime({ allowLaunch: true })
  initAutoUpdater()
  const win = createWindow()
  win.show()
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('before-quit', stopManagedSidecar)
```

Update `desktop/electron/preload.js`.

```javascript
contextBridge.exposeInMainWorld('sidecar', {
  getUrl: () => ipcRenderer.invoke('sidecar:url'),
  getRuntimeConfig: () => ipcRenderer.invoke('sidecar:get-runtime-config'),
  setRuntimeConfig: (partial) => ipcRenderer.invoke('sidecar:set-runtime-config', partial),
  getStatus: () => ipcRenderer.invoke('sidecar:get-status'),
  checkHealth: () => ipcRenderer.invoke('sidecar:check-health')
})
```

- [ ] **Step 4: Run the Node tests to verify the startup contract helper and IPC wiring compile cleanly**

Run: `node --test desktop/electron/sidecarRuntime.test.js`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add desktop/electron/sidecarRuntime.js desktop/electron/sidecarRuntime.test.js desktop/electron/main.js desktop/electron/preload.js
git commit -m "feat: add desktop sidecar startup controller"
```

## Task 3: Migrate Renderer Consumers To Main-Process Sidecar Authority

**Files:**
- Modify: `desktop/src/services/sidecarClient.js`
- Modify: `desktop/src/components/settings/SettingsPanel.jsx`
- Modify: `desktop/src/store/settingsStore.js`
- Test: `tests/contract/test_sidecar_client.py`

- [ ] **Step 1: Add failing static regression tests for renderer/main-process authority**

Extend `tests/contract/test_sidecar_client.py` with desktop-source assertions.

```python
def test_desktop_sidecar_client_reads_runtime_config_from_main_process() -> None:
    source = _read_repo_file("desktop/src/services/sidecarClient.js")

    assert "window.sidecar.getRuntimeConfig()" in source
    assert "settingsStore.getState().sidecarUrl" not in source


def test_desktop_preload_exposes_runtime_config_ipc() -> None:
    source = _read_repo_file("desktop/electron/preload.js")

    assert "getRuntimeConfig" in source
    assert "setRuntimeConfig" in source
    assert "getStatus" in source


def test_desktop_settings_store_no_longer_persists_sidecar_url() -> None:
    source = _read_repo_file("desktop/src/store/settingsStore.js")

    assert "sidecarUrl" not in source


def test_settings_panel_saves_sidecar_config_through_ipc() -> None:
    source = _read_repo_file("desktop/src/components/settings/SettingsPanel.jsx")

    assert "window.sidecar?.setRuntimeConfig" in source
    assert "resolvedUrlSource" in source
```

- [ ] **Step 2: Run the targeted contract tests to confirm the renderer still depends on local state**

Run: `python -m pytest tests/contract/test_sidecar_client.py -q`
Expected: FAIL on the new desktop-source assertions.

- [ ] **Step 3: Move sidecar URL and sidecar command editing to IPC-backed desktop config**

Replace `desktop/src/services/sidecarClient.js` with this exact version.

```javascript
/**
 * Sidecar HTTP + SSE client.
 *
 * Connects to the Python sidecar at a main-process-authoritative base URL and provides
 * methods for health checks, non-streaming calls, and SSE streaming.
 */

const DEFAULT_BASE_URL = 'http://127.0.0.1:8765'

async function getBaseUrl() {
  if (!window.sidecar?.getRuntimeConfig) return DEFAULT_BASE_URL
  const runtime = await window.sidecar.getRuntimeConfig()
  return runtime.resolvedUrl || DEFAULT_BASE_URL
}

export async function checkHealth() {
  if (window.sidecar?.checkHealth) {
    return window.sidecar.checkHealth()
  }

  const res = await fetch(`${await getBaseUrl()}/health`)
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`)
  return res.json()
}

export async function runAgent(request) {
  const res = await fetch(`${await getBaseUrl()}/agent/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }))
    throw new Error(err.message || err.error || `Agent run failed: ${res.status}`)
  }
  return res.json()
}

export function streamAgent(request, handlers = {}) {
  const controller = new AbortController()

  ;(async () => {
    let sawDone = false
    try {
      const baseUrl = await getBaseUrl()
      const res = await fetch(`${baseUrl}/agent/run/stream`, {
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
      if (err.name !== 'AbortError') {
        handlers.onError?.(err)
      }
    }
  })()

  return controller
}

export async function fetchSkills() {
  const res = await fetch(`${await getBaseUrl()}/skills`)
  if (!res.ok) throw new Error(`Fetch skills failed: ${res.status}`)
  return res.json()
}

export async function activateSkill(id) {
  const res = await fetch(`${await getBaseUrl()}/skills/${id}/activate`, { method: 'POST' })
  if (!res.ok) throw new Error(`Activate skill failed: ${res.status}`)
  return res.json()
}

export async function deactivateSkill(id) {
  const res = await fetch(`${await getBaseUrl()}/skills/${id}/deactivate`, { method: 'POST' })
  if (!res.ok) throw new Error(`Deactivate skill failed: ${res.status}`)
  return res.json()
}

export async function runFormalAnalysis(request) {
  const res = await fetch(`${await getBaseUrl()}/formal-analysis`, {
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

Update `desktop/src/store/settingsStore.js` so it drops the legacy `sidecarUrl` key instead of carrying it forward forever.

```javascript
import { create } from 'zustand'

const STORAGE_KEY = 'pyc-hermes-settings'

const DEFAULTS = {
  defaultModel: '',
  defaultAnalysisMode: 'casual',
  theme: 'dark'
}

function sanitizeSettings(input = {}) {
  return {
    defaultModel: typeof input.defaultModel === 'string' ? input.defaultModel : DEFAULTS.defaultModel,
    defaultAnalysisMode: ['casual', 'structured', 'formal'].includes(input.defaultAnalysisMode)
      ? input.defaultAnalysisMode
      : DEFAULTS.defaultAnalysisMode,
    theme: ['light', 'dark', 'system'].includes(input.theme) ? input.theme : DEFAULTS.theme
  }
}

const useSettingsStore = create((set, get) => ({
  ...DEFAULTS,

  loadSettings: () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (!raw) return
      set(sanitizeSettings(JSON.parse(raw)))
    } catch {
      // ignore corrupt storage
    }
  },

  saveSettings: (partial) => {
    const next = sanitizeSettings({ ...get(), ...partial })
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    set(next)
  }
}))

export default useSettingsStore
```

Replace `desktop/src/components/settings/SettingsPanel.jsx` with this exact version so the sidecar contract is fully IPC-backed while the other renderer preferences remain local.

```javascript
import { useState, useEffect } from 'react'
import useSettingsStore from '../../store/settingsStore'

export default function SettingsPanel({ open, onClose }) {
  const settings = useSettingsStore()
  const [form, setForm] = useState({})

  useEffect(() => {
    if (!open) return

    let cancelled = false
    async function loadForm() {
      const runtimeConfig = await window.sidecar?.getRuntimeConfig?.()
      const runtimeStatus = await window.sidecar?.getStatus?.()
      if (cancelled) return

      setForm({
        defaultModel: settings.defaultModel,
        defaultAnalysisMode: settings.defaultAnalysisMode,
        theme: settings.theme,
        sidecar_url: runtimeConfig?.persistedConfig?.sidecar_url || '',
        sidecar_command: runtimeConfig?.persistedConfig?.sidecar_command || '',
        sidecar_args_text: (runtimeConfig?.persistedConfig?.sidecar_args || []).join('\n'),
        resolvedUrl: runtimeConfig?.resolvedUrl || '',
        resolvedUrlSource: runtimeConfig?.resolvedUrlSource || 'default',
        launchCommandSource: runtimeConfig?.launchCommandSource || 'none',
        startupState: runtimeStatus?.startup_state || 'checking'
      })
    }

    loadForm()
    return () => { cancelled = true }
  }, [open, settings.defaultModel, settings.defaultAnalysisMode, settings.theme])

  if (!open) return null

  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }))

  const handleSave = async () => {
    settings.saveSettings({
      defaultModel: form.defaultModel,
      defaultAnalysisMode: form.defaultAnalysisMode,
      theme: form.theme
    })

    await window.sidecar?.setRuntimeConfig?.({
      sidecar_url: form.sidecar_url,
      sidecar_command: form.sidecar_command,
      sidecar_args: String(form.sidecar_args_text || '').split(/\r?\n/).map((line) => line.trim()).filter(Boolean)
    })

    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative w-96 h-full bg-white dark:bg-gray-900 shadow-xl flex flex-col animate-slide-in">
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Settings</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">✕</button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-5">
          <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-3 text-xs text-gray-600 dark:text-gray-300 space-y-1">
            <div><strong>Resolved URL:</strong> {form.resolvedUrl || 'Not resolved yet'}</div>
            <div><strong>URL Source:</strong> {form.resolvedUrlSource}</div>
            <div><strong>Launch Source:</strong> {form.launchCommandSource}</div>
            <div><strong>Startup State:</strong> {form.startupState}</div>
          </div>

          <Field label="Sidecar URL">
            <input type="text" value={form.sidecar_url || ''} onChange={(e) => update('sidecar_url', e.target.value)} className="input-field" />
          </Field>

          <Field label="Sidecar Launch Command">
            <input type="text" value={form.sidecar_command || ''} onChange={(e) => update('sidecar_command', e.target.value)} className="input-field" />
          </Field>

          <Field label="Sidecar Launch Args (one per line)">
            <textarea value={form.sidecar_args_text || ''} onChange={(e) => update('sidecar_args_text', e.target.value)} className="input-field min-h-28" />
          </Field>

          <Field label="Default Model">
            <input
              type="text"
              value={form.defaultModel || ''}
              onChange={(e) => update('defaultModel', e.target.value)}
              placeholder="gpt-4o, claude-sonnet-4-20250514"
              className="input-field"
            />
          </Field>

          <Field label="Default Analysis Mode">
            <select
              value={form.defaultAnalysisMode || 'casual'}
              onChange={(e) => update('defaultAnalysisMode', e.target.value)}
              className="input-field"
            >
              <option value="casual">Casual</option>
              <option value="structured">Structured</option>
              <option value="formal">Formal</option>
            </select>
          </Field>

          <Field label="Theme">
            <select
              value={form.theme || 'dark'}
              onChange={(e) => update('theme', e.target.value)}
              className="input-field"
            >
              <option value="light">Light</option>
              <option value="dark">Dark</option>
              <option value="system">System</option>
            </select>
          </Field>
        </div>

        <div className="p-4 border-t border-gray-200 dark:border-gray-700">
          <button onClick={handleSave} className="w-full px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium">Save</button>
        </div>
      </div>
    </div>
  )
}

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</span>
      <div className="mt-1">{children}</div>
    </label>
  )
}
```

- [ ] **Step 4: Run the targeted contract tests to verify the renderer now obeys main-process authority**

Run: `python -m pytest tests/contract/test_sidecar_client.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add desktop/src/services/sidecarClient.js desktop/src/components/settings/SettingsPanel.jsx desktop/src/store/settingsStore.js tests/contract/test_sidecar_client.py
git commit -m "fix: move desktop sidecar settings to main process"
```

## Task 4: Document The Startup Contract And Run Final Verification

**Files:**
- Modify: `desktop/README.md`
- Modify: `docs/Documentation_Tracking.md`
- Test: `tests/contract/test_windows_packaging.py`
- Test: `tests/integration/test_sidecar_integration.py`

- [ ] **Step 1: Add failing documentation assertions for the new startup contract**

Extend `tests/contract/test_windows_packaging.py` with README-level startup-contract checks.

```python
def test_desktop_readme_documents_sidecar_startup_contract() -> None:
    root = Path(__file__).resolve().parents[2]
    desktop_readme = (root / "desktop" / "README.md").read_text(encoding="utf-8")

    assert "PYC_HERMES_SIDECAR_URL" in desktop_readme
    assert "sidecar_url.txt" in desktop_readme
    assert "sidecar-config.json" in desktop_readme
    assert "PYC_HERMES_SIDECAR_CMD" in desktop_readme
    assert "attach first" in desktop_readme.lower()
```

- [ ] **Step 2: Run the packaging/doc tests to confirm the README does not document the new contract yet**

Run: `python -m pytest tests/contract/test_windows_packaging.py -q`
Expected: FAIL on `test_desktop_readme_documents_sidecar_startup_contract`.

- [ ] **Step 3: Update `desktop/README.md` and the docs manifest**

Add a startup-contract section to `desktop/README.md`.

```markdown
## Sidecar Startup Contract

Desktop sidecar startup is main-process authoritative.

Resolved URL precedence:

1. `PYC_HERMES_SIDECAR_URL`
2. `<userData>/sidecar_url.txt`
3. `<userData>/sidecar-config.json`
4. `http://127.0.0.1:8765`

Launch command precedence:

1. `PYC_HERMES_SIDECAR_CMD`
2. `<userData>/sidecar-config.json`
3. no launch command

Behavior:

- Desktop attaches first.
- If attach fails and a launch command is configured, Electron launches the sidecar and retries `/health` for a bounded interval.
- Renderer code reads the resolved sidecar URL through `window.sidecar` IPC rather than renderer local storage.
```

- [ ] **Step 4: Run the final A1 verification commands**

Run from repo root:

`node --test desktop/electron/sidecarRuntime.test.js`

Expected: PASS

Run from repo root:

`python -m pytest tests/contract/test_sidecar_client.py tests/contract/test_windows_packaging.py tests/integration/test_sidecar_integration.py -q`

Expected: PASS

Run from `desktop/`:

`npm run build`

Expected: `electron-vite build` completes successfully.

Run from repo root:

`python scripts/release_gates.py`

Expected: PASS with `release_gates: OK`

- [ ] **Step 5: Commit**

```bash
git add desktop/README.md docs/Documentation_Tracking.md tests/contract/test_windows_packaging.py
git commit -m "docs: define desktop sidecar startup contract"
```
