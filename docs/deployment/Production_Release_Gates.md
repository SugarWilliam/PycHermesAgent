# Production-oriented release gates (path to GA)

**Status:** Operational checklist (not a guarantee of store-ready binaries without signing/updater)

## Goals

Align automation with `docs/architecture/Execution_Blueprint_v0.2.0.md` and `docs/constraints/windows-packaging.md`:

- **Immutable install directory** — validated by `pyc-hermes-packaging-probe` and contract tests.
- **Lockfile discipline** — `uv lock --check` in production gate.
- **MRAG migration visibility** — `pyc-hermes-mrag-migrate STORAGE_ROOT` plans upgrades (no silent rewrites); index downgrades/rebuilds stay documented in the compatibility matrix.
- **Desktop artifact** — `desktop/npm run dist:dir` produces an **unpackaged** directory suitable for CI smoke; Windows installer signing, updater, and store uploads remain manual.

## Commands

| Step | Command |
|------|---------|
| Full gate (default CI) | `uv run python scripts/release_gates.py` with `RELEASE_GATES_RUFF=1`, `RELEASE_GATES_MYPY=1` |
| Production add-ons | `RELEASE_GATES_PRODUCTION=1 uv run python scripts/release_gates.py` (includes prior steps unless `--no-pytest`) |
| MRAG planner | `uv run pyc-hermes-mrag-migrate /path/to/mrag/root --json` |
| Desktop pack | `cd desktop && npm ci && npm run dist:dir` |

## Observability

Set **`PYC_HERMES_LOG_FORMAT=json`** before starting the sidecar so `log_event` lines are plain JSON objects (no log prefix noise). **`PYC_HERMES_LOG_LEVEL`** controls verbosity (`INFO` default).

## Honest scope

Neural embedding models, code signing, auto-update channels, and full migration fuzzing are **not** implied by passing these gates; they are the next layers after this automation baseline.
