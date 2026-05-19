const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('versions', {
  node: () => process.versions.node,
  chrome: () => process.versions.chrome,
  electron: () => process.versions.electron
})

contextBridge.exposeInMainWorld('sidecar', {
  getUrl: () => ipcRenderer.invoke('sidecar:url'),
  checkHealth: () => ipcRenderer.invoke('sidecar:health')
})

contextBridge.exposeInMainWorld('app', {
  getTheme: () => ipcRenderer.invoke('app:theme')
})

contextBridge.exposeInMainWorld('updater', {
  check: () => ipcRenderer.invoke('updater:check'),
  download: () => ipcRenderer.invoke('updater:download'),
  install: () => ipcRenderer.invoke('updater:install'),
  onStatus: (callback) => ipcRenderer.on('updater:status', (_, data) => callback(data))
})
