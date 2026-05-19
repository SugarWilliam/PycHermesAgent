const { app, BrowserWindow, ipcMain } = require('electron')
const { join } = require('path')
const http = require('http')

let autoUpdater = null
try { autoUpdater = require('electron-updater').autoUpdater } catch (e) { /* dev mode */ }

const SIDECAR_URL = process.env.PYC_HERMES_SIDECAR_URL || 'http://127.0.0.1:8765'

function checkSidecarHealth() {
  return new Promise((resolve) => {
    const url = new URL('/health', SIDECAR_URL)
    const req = http.get(url, (res) => {
      let body = ''
      res.on('data', (chunk) => { body += chunk })
      res.on('end', () => {
        resolve({ ok: res.statusCode === 200, status: res.statusCode, body })
      })
    })
    req.on('error', (err) => resolve({ ok: false, error: err.message }))
    req.setTimeout(3000, () => { req.destroy(); resolve({ ok: false, error: 'timeout' }) })
  })
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
      sandbox: false
    }
  })

  if (process.env.ELECTRON_RENDERER_URL) {
    mainWindow.loadURL(process.env.ELECTRON_RENDERER_URL)
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }

  return mainWindow
}

ipcMain.handle('sidecar:health', () => checkSidecarHealth())
ipcMain.handle('sidecar:url', () => SIDECAR_URL)

function initAutoUpdater() {
  if (!autoUpdater) return
  autoUpdater.autoDownload = false
  autoUpdater.autoInstallOnAppQuit = true

  function sendStatus(data) {
    const win = BrowserWindow.getAllWindows()[0]
    if (win && !win.isDestroyed()) win.webContents.send('updater:status', data)
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
  const healthy = await checkSidecarHealth()
  if (!healthy.ok) {
    console.warn('[desktop] Sidecar not reachable at', SIDECAR_URL)
  }

  initAutoUpdater()
  const win = createWindow()

  win.once('show', () => {
    if (autoUpdater) setTimeout(() => autoUpdater.checkForUpdates().catch(() => {}), 5000)
  })
  win.show()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
