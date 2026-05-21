const { app, BrowserWindow, ipcMain } = require('electron')
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
  const nextRuntimeConfig = resolveSidecarRuntimeConfig({ env: process.env, userDataDir: app.getPath('userData') })

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
  await refreshSidecarRuntime({ allowLaunch: false })
  return { ...runtimeConfig, persisted_config: next }
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
