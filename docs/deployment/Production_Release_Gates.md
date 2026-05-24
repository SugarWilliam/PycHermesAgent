# Production-oriented release gates (path to GA)

**Status:** Operational checklist (not a guarantee of store-ready binaries without signing/updater)

**Governance linkage:** Routine **tranche-one** tagging follows `docs/Project_Development_and_Release_Governance.md` Gates 1–8. **`Gate 9`** (Phase 5 / major architecture fork) applies only **after Phase 4 tranche-one closure** and when a release is explicitly Phase 5–scoped — see **§ Gate 9 — Phase 5 / architecture fork** below.

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

## Gate 9 — Phase 5 / architecture fork (manual until scripted)

Use this subsection **only** when tagging a release that executes **`docs/architecture/Phase5_Evolution_Blueprint_v0.5.0.md`** work (gateway/runtime fork, cross-cutting teammate surfaces, coordinated contract bumps). It **does not** replace Gates 1–8; **it adds** prerequisites on top.

| # | Checkpoint | Receipt / artefact |
|---|------------|---------------------|
| 9a | Phase 4 tranche-one closure is still the baseline for ordinary releases; Gate 9 applies only after **explicit Phase 5 program open** | Record in release notes (`Phase 5 program open`) or steering doc link |
| 9b | **ADR published** summarising fork choice (`llm_gateway` deepen vs upstream gateway integration vs hybrid); linked from release notes | ADR filename + anchor in changelog |
| 9c | **`docs/architecture/Compatibility_Matrix.md` §6** satisfied: every touched axis (`sidecar_api_version`, `contract_version`, `desktop_ipc_version`, `index_format_version`, …) bumped **together** with a single migration narrative | Updated matrix §5 table + subsection §6 wording still true |
| 9d | **`AGENTS.md` / governance §4** non‑negotiables unchanged unless the ADR explicitly revises boundaries (then `AGENTS.md` + governance must be patched in the **same** release merge) | Diff shows intentional boundary edits only via ADR |
| 9e | Contract suite and any **new** migration / desktop IPC tests required by the fork pass in CI | Log excerpt or CI run URL in release checklist |
| 9f | If route B / vendor gateway: **exit / self-host rollback** posture documented (per blueprint §7 vendor lock‑in guard) | Paragraph in ADR attachment or ops runbook |

**Authoritative charters:** `docs/architecture/Phase5_Evolution_Blueprint_v0.5.0.md`, `docs/Project_Development_and_Release_Governance.md` §9, `docs/architecture/Compatibility_Matrix.md` §§5–6.

## Honest scope

Neural embedding models, code signing, auto-update channels, and full migration fuzzing are **not** implied by passing these gates; they are the next layers after this automation baseline.
