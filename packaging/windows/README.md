# Windows packaging preview (engineering prototype)

This directory contains a **non-production** launcher that enforces the directory policy from `docs/constraints/windows-packaging.md`:

- Writable state uses `%APPDATA%` / `%LOCALAPPDATA%` (or overridden `LOCALAPPDATA` / `APPDATA` for tests).
- `--root` points at the **read-only workspace / install tree** for config and skill discovery only.
- `PYC_HERMES_ENFORCE_PACKAGING_RULES=1` prevents the sandbox under `--root` from receiving MRAG, models, artifacts, or logs.

## Run (preview)

From a **developer** clone (repo root as logical install):

```powershell
cd packaging\windows
.\Run-SidecarPreview.ps1 -Port 8765
```

Equivalent environment for manual invocation:

```powershell
$env:PYC_HERMES_ENFORCE_PACKAGING_RULES = "1"
$env:PYC_HERMES_INSTALL_DIR = "C:\path\to\repo-or-install-root"
pyc-hermes-sidecar --root $env:PYC_HERMES_INSTALL_DIR --port 8765
```

Inspect resolved paths (JSON):

```powershell
pyc-hermes-packaging-probe --workspace-root C:\path\to\repo-or-install-root --mkdirs
```

## Not included in this prototype

Code signing, MSIX/MSI installers, elevation UX, updater, and full crash-durability guarantees for promotion (see constraint doc §2).
