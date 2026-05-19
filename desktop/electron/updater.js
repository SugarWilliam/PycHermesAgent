/**
 * Auto-update manager using electron-updater.
 * Checks GitHub Releases for new versions.
 * Auto-download disabled — user must opt in.
 */
const { autoUpdater } = require('electron-updater')
const { BrowserWindow, ipcMain } = require('electron')

function sendStatus(data) {
  const win = BrowserWindow.getAllWindows()[0]
  if (win && !win.isDestroyed()) {
    win.webContents.send('updater:status', data)
  }
}

function initAutoUpdater() {
  autoUpdater.autoDownload = false
  autoUpdater.autoInstallOnAppQuit = true

  autoUpdater.on('checking-for-update', () => {
    sendStatus({ state: 'checking' })
  })

  autoUpdater.on('update-available', (info) => {
    sendStatus({ state: 'available', version: info.version, releaseNotes: info.releaseNotes })
  })

  autoUpdater.on('update-not-available', () => {
    sendStatus({ state: 'none' })
  })

  autoUpdater.on('download-progress', (progress) => {
    sendStatus({ state: 'downloading', percent: Math.round(progress.percent) })
  })

  autoUpdater.on('update-downloaded', (info) => {
    sendStatus({ state: 'ready', version: info.version })
  })

  autoUpdater.on('error', (err) => {
    sendStatus({ state: 'error', message: err ? err.message : 'Unknown error' })
  })

  ipcMain.handle('updater:check', () => autoUpdater.checkForUpdates())
  ipcMain.handle('updater:download', () => autoUpdater.downloadUpdate())
  ipcMain.handle('updater:install', () => autoUpdater.quitAndInstall())
}

function checkForUpdates() {
  autoUpdater.checkForUpdates().catch(() => {})
}

module.exports = { initAutoUpdater, checkForUpdates }
