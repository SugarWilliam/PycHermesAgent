# PycHermesAgent desktop shell (preview)

Engineering-preview **Electron** wrapper around the **Python sidecar** (`pyc-hermes-sidecar`). It does not bundle Python; it displays `/health` from a running sidecar.

## Prerequisites

- Node.js 20+
- Python environment with `pyc-hermes-sidecar` on PATH (or use `PYC_HERMES_SIDECAR_CMD`)

## Run

Terminal A (repo root, virtualenv active):

```bash
pyc-hermes-sidecar --host 127.0.0.1 --port 8765
```

Terminal B:

```bash
cd desktop
npm install
npm start
```

## Environment

| Variable | Meaning |
|----------|---------|
| `PYC_HERMES_SIDECAR_URL` | Base URL of the sidecar (default `http://127.0.0.1:8765`) |
| `PYC_HERMES_SIDECAR_CMD` | Optional shell command to spawn the sidecar before opening the window (advanced) |

Packaging, auto-update, and install-directory boundaries are **not** implemented in this preview; see `docs/constraints/windows-packaging.md` and governance documents.
