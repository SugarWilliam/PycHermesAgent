# PycHermesAgent desktop shell (preview)

Engineering-preview **Electron** wrapper around the **Python sidecar** (`pyc-hermes-sidecar`). It does not bundle Python; it displays `/health` (summary + raw JSON) and key paths from **`GET /runtime-paths`**. **File → Open logs folder / Open local data folder** uses `shell.openPath` when paths are available. **View → Refresh sidecar status** (Ctrl+R / Cmd+R) re-probes the sidecar without restarting the desktop app.

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

## Sidecar URL without environment (optional)

Resolution order: **`PYC_HERMES_SIDECAR_URL`** (if set) → plain-text file **`sidecar_url.txt`** in the Electron **user data** directory (first non-empty, non-`#` line, full URL) → default `http://127.0.0.1:8765`.

From the app menu use **View → Open desktop config folder**, then create or edit `sidecar_url.txt`, or use **View → Create sidecar_url.txt template…** once to drop a commented default file. Restart is not required: **View → Refresh** reloads the file.

On first connect failure the shell **retries up to 5 times** with increasing delay (helps if the sidecar starts slightly after the desktop window).

Packaging, auto-update, and install-directory boundaries are **not** implemented in this preview; see `docs/constraints/windows-packaging.md` and governance documents.
