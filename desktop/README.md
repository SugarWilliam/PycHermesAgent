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
npm run dist:dir   # unpacked build for testing
npm run dist       # full installer
```

## Architecture

- `electron/main.js` — Electron main process, sidecar health probe
- `electron/preload.js` — contextBridge IPC exposure
- `src/` — React renderer (Vite + Tailwind)
- `electron.vite.config.js` — electron-vite build configuration
