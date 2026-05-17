# Windows Packaging Constraints

**Status:** Hard constraint

## 1. Directory Policy

The install directory is read-only. Runtime writes must never target the install directory.

Required layout:

| Data Class | Location |
|------------|----------|
| user configuration | `%APPDATA%` equivalent |
| logs | `%LOCALAPPDATA%` equivalent |
| caches | `%LOCALAPPDATA%` equivalent |
| MRAG indexes | `%LOCALAPPDATA%` equivalent |
| downloads | `%LOCALAPPDATA%` equivalent |
| model assets | `%LOCALAPPDATA%` equivalent |
| artifacts | `%LOCALAPPDATA%` equivalent |

## 2. Model and Asset Promotion

Model downloads and asset installation must use:

- staging directory,
- checksum validation,
- manifest validation,
- atomic promotion where supported,
- no mutation of install directory.

The current staging rename foundation is not a full fsync, crash-durability, or cross-process locking guarantee. Production claims require additional tests and documented behavior.

## 3. Sidecar and Desktop Boundary

The Electron shell may launch and supervise the sidecar, but sidecar runtime state remains owned by the Python sidecar modules. Desktop code must not bypass sidecar contracts to mutate MRAG indexes, model assets, or artifact records.

## 4. Release Packaging Gate

A Windows release package cannot be tagged production-ready until:

- runtime path tests pass,
- install-directory immutability is tested,
- asset promotion tests pass,
- sidecar health smoke passes after install,
- upgrade/migration behavior is documented,
- no local secrets or runtime state are packaged.

## 5. Cursor Automation Boundary

Cursor may automate push, tag, and release preparation only after packaging gates pass for the intended release class. Cursor must stop when signing, installer credentials, store upload credentials, or destructive git operations are required but not explicitly available and verified.

## 6. Executable prototype (preview)

The repository ships a **non-production** Windows launcher and path probe:

- `packaging/windows/Run-SidecarPreview.ps1` sets `PYC_HERMES_ENFORCE_PACKAGING_RULES` and starts the sidecar with a read-only `--root`.
- Console entry point `pyc-hermes-packaging-probe` prints resolved runtime paths and validates `PYC_HERMES_INSTALL_DIR` when enforcement is enabled.

These prototypes do **not** satisfy the production packaging gate in §4; they exist to make constraints testable and operable during development.
