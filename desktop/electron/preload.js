const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('versions', {
  node: () => process.versions.node,
  chrome: () => process.versions.chrome,
  electron: () => process.versions.electron,
})

contextBridge.exposeInMainWorld('sidecar', {
  getUrl: () => ipcRenderer.invoke('sidecar:url'),
  getRuntimeConfig: () => ipcRenderer.invoke('sidecar:get-runtime-config'),
  setRuntimeConfig: (partial) => ipcRenderer.invoke('sidecar:set-runtime-config', partial),
  getStatus: () => ipcRenderer.invoke('sidecar:get-status'),
  checkHealth: () => ipcRenderer.invoke('sidecar:health'),
  restart: () => ipcRenderer.invoke('sidecar:restart'),
})

contextBridge.exposeInMainWorld('app', {
  getTheme: () => ipcRenderer.invoke('app:theme'),
})

contextBridge.exposeInMainWorld('updater', {
  check: () => ipcRenderer.invoke('updater:check'),
  download: () => ipcRenderer.invoke('updater:download'),
  install: () => ipcRenderer.invoke('updater:install'),
  onStatus: (callback) => ipcRenderer.on('updater:status', (_, data) => callback(data)),
})

/** Host OS integration — only available inside Electron preload. */
contextBridge.exposeInMainWorld('desktopHost', {
  openPath: (absolutePath) => ipcRenderer.invoke('shell:open-path', absolutePath),
  pickFiles: (options) => ipcRenderer.invoke('dialog:open-file', options),
  setProviderEnv: (vars) => ipcRenderer.invoke('sidecar:set-provider-env', vars),
  openExternal: (url) => ipcRenderer.invoke('auth:open-external', url),
  githubDeviceCodeStart: () => ipcRenderer.invoke('auth:github-device-code-start'),
  githubDeviceCodePoll: (deviceCode) => ipcRenderer.invoke('auth:github-device-code-poll', { device_code: deviceCode }),
})

contextBridge.exposeInMainWorld('fileSystem', {
  readDir: (dirPath) => ipcRenderer.invoke('fs:read-dir', dirPath),
  readFile: (filePath) => ipcRenderer.invoke('fs:read-file', filePath),
  writeFile: (filePath, content) => ipcRenderer.invoke('fs:write-file', { filePath, content }),
  pickFolder: () => ipcRenderer.invoke('dialog:open-folder'),
})
