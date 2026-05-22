# Production-oriented release gates (path to GA)

**Status:** Operational checklist (not a guarantee of store-ready binaries without signing/updater)

## Goals

Align automation with `docs/architecture/Execution_Blueprint_v0.2.0.md` and `docs/constraints/windows-packaging.md`:

- **Immutable install directory** — validated by `pyc-hermes-packaging-probe` and contract tests.
- **Lockfile discipline** — `uv lock --check` in production gate.
- **MRAG migration visibility** — `pyc-hermes-mrag-migrate STORAGE_ROOT` plans upgrades (no silent rewrites); index downgrades/rebuilds stay documented in the compatibility matrix.
- **Desktop artifact** — `cd desktop && npm run dist:dir` produces the unpacked Electron output checked by the current production gate packaging step; installer signing, updater, and store uploads stay manual.

## Commands

| Step | Command |
|------|---------|
| Full gate (default CI) | `uv run python scripts/release_gates.py` with `RELEASE_GATES_RUFF=1`, `RELEASE_GATES_MYPY=1` |
| Production add-ons | `RELEASE_GATES_PRODUCTION=1 uv run python scripts/release_gates.py` (includes prior steps unless `--no-pytest`). Also exports **CycloneDX 1.5** Python SBOM to `build/sbom-python.cdx.json` (`build/` gitignored). |
| MRAG planner + backup | `uv run pyc-hermes-mrag-migrate /path/to/mrag/root --backup-to /path/to/backup-parent --json` |
| Desktop pack | `cd desktop && npm ci && npm audit --omit=dev --audit-level=critical && npm run dist:dir` |

**Linux vs Windows unpacked:** CI production gates exercise `dist:dir` on Ubuntu (electron-builder emits `dist-installer/linux-unpacked`). For **Windows unpacked** artifacts (Phase 3 Track G installer smoke precursor), run on **`windows-latest`** or a developer machine: `npm run dist:win-unpacked` after adding `desktop/build/icon.ico` (referenced by `package.json` `build.win.icon`).

Production gates also honour **`RELEASE_GATES_PYINSTALLER=1`** (runs **`uv sync --frozen --extra dev --extra ga`** then verifies **`PyInstaller`** imports; **`frozen`** avoids unexpected lock churn).

## Observability

Set **`PYC_HERMES_LOG_FORMAT=json`** before starting the sidecar so `log_event` lines are plain JSON objects (no log prefix noise). **`PYC_HERMES_LOG_LEVEL`** controls verbosity (`INFO` default).

`/health` includes **`observability.logs_dir`** and **`observability.sidecar_events_log`** when the sidecar is started with `--root`; disable the rotating file sink with **`PYC_HERMES_DISABLE_FILE_LOG=1`**.

## Honest scope

Neural embedding models, code signing, auto-update channels, and full migration fuzzing are **not** implied by passing these gates; they are the next layers after this automation baseline.
