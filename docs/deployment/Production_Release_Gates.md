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
| Expanded MRAG benchmark | `uv run python benchmarks/mrag/run_expanded_hybrid_benchmark.py` |
| IPC-style business MRAG benchmark | `uv run python benchmarks/mrag/run_ipc_business_hybrid_benchmark.py` |
| Desktop pack | `cd desktop && npm ci && npm audit --omit=dev --audit-level=critical && npm run dist:dir` |
| Electron unpacked layout smoke | `python scripts/electron_dist_layout_smoke.py desktop --require-unpacked-resources` (after dist; pass `--prefer-unpacked win` or `linux`; verifies `desktop/out/` and unpacked `dist-installer/*unpacked/resources/`) |
| Windows NSIS headless smoke | **From dir:** `pwsh scripts/windows_nsis_silent_upgrade_smoke.ps1 -DistDir desktop/dist-installer`; **dual semver (CI):** `-PreviousInstaller` + `-UpgradeInstaller` (+ `-ExpectedVersionSubstringAfterUpgrade`) — see **`desktop-windows-nsis-silent`**. |

**MRAG benchmarks (production gate):** The expanded hybrid script and the IPC-style business benchmark both run automatically when ``RELEASE_GATES_PRODUCTION=1`` / ``scripts/release_gates.py --with-production`` reaches the migrate + benchmark section.

**Linux vs Windows unpacked:** CI **contract-tests** exercises Linux `dist-installer/*-unpacked` via `production-gates`.
The dedicated **`desktop-windows-unpacked`** workflow job (``windows-latest``) runs ``npm run dist:win-unpacked`` **and**
**`scripts/electron_dist_layout_smoke.py ... --require-unpacked win`** so Windows
artifacts get the same structural checks as Linux. **`desktop-windows-nsis-silent`** builds **two sequential Setups** (`0.99.0-ci.prev` then `0.99.1-ci.next`), runs **`windows_nsis_silent_upgrade_smoke.ps1`** in **dual-upgrade** mode (silent prefix install → silent upgrades → PE version sanity → uninstaller `/S`).
**electron-updater** integration (HTTP feed + delta download) stays a separate gate once a publish URL exists.
Installer signing and store uploads remain manual.

Production gates also honour **`RELEASE_GATES_PYINSTALLER=1`** (runs **`uv sync --frozen --extra dev --extra ga`** then verifies **`PyInstaller`** imports; **`frozen`** avoids unexpected lock churn).

## Observability

Set **`PYC_HERMES_LOG_FORMAT=json`** before starting the sidecar so `log_event` lines are plain JSON objects (no log prefix noise). **`PYC_HERMES_LOG_LEVEL`** controls verbosity (`INFO` default).

`/health` includes **`observability.logs_dir`** and **`observability.sidecar_events_log`** when the sidecar is started with `--root`; disable the rotating file sink with **`PYC_HERMES_DISABLE_FILE_LOG=1`**.

## Honest scope

Neural embedding models, code signing, auto-update channels, and full migration fuzzing are **not** implied by passing these gates; they are the next layers after this automation baseline.
