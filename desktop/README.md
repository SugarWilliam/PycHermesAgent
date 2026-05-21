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

- Desktop uses an attach first policy.
- If attach fails and a launch command is configured, Electron launches the sidecar and retries `/health` for a bounded interval.
- Renderer code reads the resolved sidecar URL through `window.sidecar` IPC rather than renderer local storage.

## Architecture

- `electron/main.js` — Electron main process, sidecar health probe
- `electron/preload.js` — contextBridge IPC exposure
- `src/` — React renderer (Vite + Tailwind)
- `electron.vite.config.js` — electron-vite build configuration
