const { app, BrowserWindow, ipcMain, shell, dialog } = require('electron')
const { join } = require('path')

let autoUpdater = null
try {
  autoUpdater = require('electron-updater').autoUpdater
} catch (e) {
  // dev mode
}

const {
  buildSidecarStatus,
  buildManagedExitStatus,
  loadPersistedSidecarConfig,
  savePersistedSidecarConfig,
  resolveSidecarRuntimeConfig,
  runtimeTargetsDiffer,
  probeSidecarHealth,
  attachFirstStartup,
} = require('./sidecarRuntime')

let runtimeConfig = {
  resolved_url: 'http://127.0.0.1:8765',
  resolved_url_source: 'default',
  launch_configured: false,
  launch_command: '',
  launch_args: [],
  launch_command_source: 'none',
  persisted_config: { sidecar_url: '', sidecar_command: '', sidecar_args: [] },
}
let runtimeStatus = buildSidecarStatus(runtimeConfig)
let managedSidecar = null

async function checkSidecarHealth() {
  const SIDECAR_URL = runtimeConfig.resolved_url
  const probe = await probeSidecarHealth(SIDECAR_URL)
  const parsed = probe.payload || null
  const body = probe.rawBody
  return {
    ok: probe.ok,
    status: probe.status,
    url: SIDECAR_URL,
    payload: parsed,
    rawBody: parsed ? undefined : body,
    error: probe.error,
  }
}

function createWindow() {
  const mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    title: 'PycHermesAgent',
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  })

  if (process.env.ELECTRON_RENDERER_URL) {
    mainWindow.loadURL(process.env.ELECTRON_RENDERER_URL)
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }

  return mainWindow
}

function stopManagedSidecar() {
  if (managedSidecar && !managedSidecar.killed) {
    managedSidecar.kill()
  }
  managedSidecar = null
}

function bindManagedSidecar(child, runtime) {
  if (!child || typeof child.once !== 'function') {
    return child
  }

  child.once('exit', (code, signal) => {
    if (managedSidecar !== child) {
      return
    }
    runtimeStatus = buildManagedExitStatus(runtime, runtimeStatus, { code, signal })
    managedSidecar = null
  })
  return child
}

async function refreshSidecarRuntime({ allowLaunch }) {
  const nextRuntimeConfig = resolveSidecarRuntimeConfig({ env: process.env, userDataDir: app.getPath('userData'), resourcesPath: process.resourcesPath || '' })

  if (managedSidecar && runtimeTargetsDiffer(runtimeConfig, nextRuntimeConfig)) {
    stopManagedSidecar()
  }

  runtimeConfig = nextRuntimeConfig

  if (allowLaunch) {
    const result = await attachFirstStartup(runtimeConfig)
    runtimeStatus = result.status
    managedSidecar = result.status.managed_process ? bindManagedSidecar(result.child, runtimeConfig) : null
    return runtimeStatus
  }

  const probe = await probeSidecarHealth(runtimeConfig.resolved_url)
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
ipcMain.handle('sidecar:health', async () => checkSidecarHealth())
ipcMain.handle('sidecar:url', async () => runtimeConfig.resolved_url)
ipcMain.handle('sidecar:set-runtime-config', async (_event, partial) => {
  const current = loadPersistedSidecarConfig(app.getPath('userData'))
  const next = savePersistedSidecarConfig(app.getPath('userData'), {
    sidecar_url: typeof partial.sidecar_url === 'string' ? partial.sidecar_url : current.sidecar_url,
    sidecar_command: typeof partial.sidecar_command === 'string' ? partial.sidecar_command : current.sidecar_command,
    sidecar_args: Array.isArray(partial.sidecar_args) ? partial.sidecar_args : current.sidecar_args,
  })
  // Saving desktop sidecar settings should re-run attach-first startup so a
  // configured launch command can spawn the managed sidecar without a separate
  // "Restart sidecar" action (Phase 3A product path).
  await refreshSidecarRuntime({ allowLaunch: true })
  return { ...runtimeConfig, persisted_config: next }
})
ipcMain.handle('sidecar:restart', async () => {
  await refreshSidecarRuntime({ allowLaunch: true })
  return runtimeStatus
})

/** Best-effort open of an absolute file path from the renderer (exported artifacts). */
ipcMain.handle('shell:open-path', async (_event, filepath) => {
  const fp = typeof filepath === 'string' ? filepath.trim() : ''
  if (!fp) return { ok: false, error: 'empty_path' }
  const err = await shell.openPath(fp)
  return { ok: !err, error: err || null }
})

/** Open a native file-picker dialog and return selected file paths. */
ipcMain.handle('dialog:open-file', async (_event, options) => {
  const win = BrowserWindow.getAllWindows()[0]
  const result = await dialog.showOpenDialog(win, {
    title: options?.title || 'Select files',
    properties: ['openFile', ...(options?.multiple ? ['multiSelections'] : [])],
    filters: options?.filters || [
      { name: 'Documents', extensions: ['md', 'txt', 'pdf', 'docx', 'xlsx', 'pptx', 'html', 'htm'] },
      { name: 'Images', extensions: ['png', 'jpg', 'jpeg', 'gif', 'webp', 'tif', 'tiff', 'bmp'] },
      { name: 'All Files', extensions: ['*'] }
    ]
  })
  return { canceled: result.canceled, filePaths: result.filePaths || [] }
})

/** Store provider environment variables and pass them to managed sidecar on next restart. */
let providerEnvOverrides = {}
ipcMain.handle('sidecar:set-provider-env', async (_event, vars) => {
  if (vars && typeof vars === 'object') {
    providerEnvOverrides = { ...providerEnvOverrides, ...vars }
    // Persist to userData for next launch
    const fs = require('fs')
    const path = require('path')
    const envFile = path.join(app.getPath('userData'), 'provider-env.json')
    try { fs.writeFileSync(envFile, JSON.stringify(providerEnvOverrides, null, 2)) } catch {}
    // Also inject into current process env so sidecar can pick up on restart
    for (const [k, v] of Object.entries(vars)) {
      if (v) process.env[k] = v
      else delete process.env[k]
    }
  }
  return { ok: true }
})

// === Filesystem IPC for file explorer ===
ipcMain.handle('fs:read-dir', async (_event, dirPath) => {
  const fs = require('fs')
  const path = require('path')
  try {
    const entries = fs.readdirSync(dirPath, { withFileTypes: true })
    const items = entries.map(e => ({
      name: e.name,
      path: path.join(dirPath, e.name),
      isDirectory: e.isDirectory(),
    })).sort((a, b) => {
      if (a.isDirectory !== b.isDirectory) return a.isDirectory ? -1 : 1
      return a.name.localeCompare(b.name)
    })
    return { ok: true, items }
  } catch (err) {
    return { ok: false, error: err.message }
  }
})

ipcMain.handle('fs:read-file', async (_event, filePath) => {
  const fs = require('fs')
  try {
    const stat = fs.statSync(filePath)
    if (stat.size > 5 * 1024 * 1024) {
      return { ok: false, error: 'File too large (>5MB)' }
    }
    const content = fs.readFileSync(filePath, 'utf-8')
    return { ok: true, content, size: stat.size }
  } catch (err) {
    return { ok: false, error: err.message }
  }
})

ipcMain.handle('fs:write-file', async (_event, { filePath, content }) => {
  const fs = require('fs')
  try {
    fs.writeFileSync(filePath, content, 'utf-8')
    return { ok: true }
  } catch (err) {
    return { ok: false, error: err.message }
  }
})

ipcMain.handle('dialog:open-folder', async () => {
  const win = BrowserWindow.getAllWindows()[0]
  const result = await dialog.showOpenDialog(win, {
    title: '选择文件夹',
    properties: ['openDirectory']
  })
  return { canceled: result.canceled, filePaths: result.filePaths || [] }
})

function initAutoUpdater() {
  if (!autoUpdater) return
  autoUpdater.autoDownload = false
  autoUpdater.autoInstallOnAppQuit = true

  function sendStatus(data) {
    const win = BrowserWindow.getAllWindows()[0]
    if (win && !win.isDestroyed()) {
      win.webContents.send('updater:status', data)
    }
  }

  autoUpdater.on('checking-for-update', () => sendStatus({ state: 'checking' }))
  autoUpdater.on('update-available', (info) => sendStatus({ state: 'available', version: info.version }))
  autoUpdater.on('update-not-available', () => sendStatus({ state: 'none' }))
  autoUpdater.on('download-progress', (p) => sendStatus({ state: 'downloading', percent: Math.round(p.percent) }))
  autoUpdater.on('update-downloaded', (info) => sendStatus({ state: 'ready', version: info.version }))
  autoUpdater.on('error', (err) => sendStatus({ state: 'error', message: err?.message || 'Unknown' }))

  ipcMain.handle('updater:check', () => autoUpdater.checkForUpdates())
  ipcMain.handle('updater:download', () => autoUpdater.downloadUpdate())
  ipcMain.handle('updater:install', () => autoUpdater.quitAndInstall())
}

app.whenReady().then(async () => {
  // Load persisted provider env vars (API keys etc.)
  try {
    const fs = require('fs')
    const path = require('path')
    const envFile = path.join(app.getPath('userData'), 'provider-env.json')
    if (fs.existsSync(envFile)) {
      const saved = JSON.parse(fs.readFileSync(envFile, 'utf-8'))
      for (const [k, v] of Object.entries(saved)) {
        if (v && !process.env[k]) process.env[k] = v
      }
      providerEnvOverrides = saved
    }
  } catch {}

  await refreshSidecarRuntime({ allowLaunch: true })
  initAutoUpdater()
  const win = createWindow()

  win.once('show', () => {
    if (autoUpdater) {
      setTimeout(() => autoUpdater.checkForUpdates().catch(() => {}), 5000)
    }
  })
  win.show()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('before-quit', stopManagedSidecar)

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

// ============================================================
// GitHub Copilot Device Code OAuth Flow
// ============================================================
const https = require('https')

const GITHUB_DEVICE_CODE_CLIENT_ID = 'Iv1.b507a08c87ecfe98'
const GITHUB_DEVICE_CODE_URL = 'https://github.com/login/device/code'
const GITHUB_TOKEN_URL = 'https://github.com/login/oauth/access_token'

function httpsPost(url, body, headers = {}) {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url)
    const postData = typeof body === 'string' ? body : JSON.stringify(body)
    const options = {
      hostname: parsed.hostname,
      port: 443,
      path: parsed.pathname + parsed.search,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        'Content-Length': Buffer.byteLength(postData),
        ...headers,
      },
    }
    const req = https.request(options, (res) => {
      let data = ''
      res.on('data', (chunk) => { data += chunk })
      res.on('end', () => {
        try { resolve({ status: res.statusCode, body: JSON.parse(data) }) }
        catch { resolve({ status: res.statusCode, body: data }) }
      })
    })
    req.on('error', reject)
    req.setTimeout(15000, () => { req.destroy(); reject(new Error('timeout')) })
    req.write(postData)
    req.end()
  })
}

/** Start device code flow: returns { user_code, verification_uri, device_code, interval, expires_in } */
ipcMain.handle('auth:github-device-code-start', async () => {
  try {
    const res = await httpsPost(GITHUB_DEVICE_CODE_URL, {
      client_id: GITHUB_DEVICE_CODE_CLIENT_ID,
      scope: 'read:user',
    })
    if (res.status !== 200 || !res.body?.user_code) {
      return { ok: false, error: res.body?.error_description || res.body?.error || 'Failed to get device code' }
    }
    return { ok: true, ...res.body }
  } catch (err) {
    return { ok: false, error: err.message }
  }
})

/** Poll for token: pass device_code. Returns { ok, token } or { ok: false, status: 'pending'|'error', error } */
ipcMain.handle('auth:github-device-code-poll', async (_event, { device_code }) => {
  try {
    const res = await httpsPost(GITHUB_TOKEN_URL, {
      client_id: GITHUB_DEVICE_CODE_CLIENT_ID,
      device_code,
      grant_type: 'urn:ietf:params:oauth:grant-type:device_code',
    })
    const body = res.body
    if (body?.access_token) {
      // Store the token
      providerEnvOverrides.GITHUB_TOKEN = body.access_token
      process.env.GITHUB_TOKEN = body.access_token
      const fs = require('fs')
      const path = require('path')
      const envFile = path.join(app.getPath('userData'), 'provider-env.json')
      try { fs.writeFileSync(envFile, JSON.stringify(providerEnvOverrides, null, 2)) } catch {}
      return { ok: true, token: body.access_token }
    }
    if (body?.error === 'authorization_pending') {
      return { ok: false, status: 'pending' }
    }
    if (body?.error === 'slow_down') {
      return { ok: false, status: 'slow_down' }
    }
    if (body?.error === 'expired_token') {
      return { ok: false, status: 'expired', error: 'Device code expired. Please start again.' }
    }
    return { ok: false, status: 'error', error: body?.error_description || body?.error || 'Unknown error' }
  } catch (err) {
    return { ok: false, status: 'error', error: err.message }
  }
})

/** Open URL in default browser */
ipcMain.handle('auth:open-external', async (_event, url) => {
  if (url && typeof url === 'string' && url.startsWith('https://')) {
    await shell.openExternal(url)
    return { ok: true }
  }
  return { ok: false, error: 'Invalid URL' }
})
