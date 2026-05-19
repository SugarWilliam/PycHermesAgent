# Phase 3G - Windows Release Hardening Plan v0.3.0

**Status:** Proposed execution plan
**Authority:** `docs/Project_Development_and_Release_Governance.md`
**Parent roadmap:** `docs/architecture/Phase3_Phase4_Productization_Roadmap_v0.3.0.md`
**Goal:** Move the Windows desktop and sidecar delivery path from preview-grade packaging to release-grade build, install, update, and validation discipline.

---

## 1. Scope

Phase 3G focuses on release readiness rather than new product features.

In scope:

- CI packaging coverage
- clean-machine install smoke
- updater release flow
- signing preparation
- upgrade and downgrade validation
- stronger release gates

Out of scope:

- claiming production readiness before all gates pass
- bypassing signing or updater safety checks
- storing mutable runtime state in the install directory

---

## 2. Current Baseline

Current completed baseline includes:

- `desktop/package.json` supports `electron-builder`
- updater wiring exists in the desktop main process
- `packaging/windows/Run-SidecarPreview.ps1` and packaging probe prototypes exist
- CI runs contract tests and production gate extras on Linux
- `scripts/release_gates.py` already covers whitespace, secret heuristics, optional production extras, MRAG migrate smoke, and desktop build checks

Current gap:

- No validated clean-Windows install flow is documented as complete.
- CI does not yet provide full Windows desktop release confidence.
- Signing and updater release mechanics are not fully operationalized.

---

## 3. Architecture Rules

- Install directory stays read-only.
- Runtime state remains under `%APPDATA%` and `%LOCALAPPDATA%` as defined by packaging policy.
- Desktop may supervise the sidecar, but not bypass sidecar-owned state domains.
- Release claims must not outrun verified gates.

---

## 4. Workstreams

### G1. Desktop CI Packaging Coverage

**Goal:** build confidence in desktop packaging continuously, not just locally.

Target files:

- `.github/workflows/ci.yml`
- `.github/workflows/release.yml`
- `desktop/package.json`

Required outcomes:

- Desktop build and packaging checks run in CI where appropriate.
- Failure signals are visible before release preparation.

Acceptance:

- CI can produce or validate desktop packaging artifacts consistently.

### G2. Clean-Machine Install Validation

**Goal:** verify the packaged product on a real Windows environment without developer-state leakage.

Target files:

- `docs/deployment/*`
- `packaging/windows/*`
- `tests/contract/test_windows_packaging.py`

Required outcomes:

- Install smoke checklist exists and is executable.
- Startup, health, and desktop launch behavior are validated on clean systems.

Acceptance:

- Installer smoke passes on a clean Windows environment.

### G3. Updater Release Flow

**Goal:** make the updater path a real release feature instead of configuration-only code.

Target files:

- `desktop/electron/main.js`
- `desktop/src/components/settings/UpdateNotification.jsx`
- `desktop/package.json`
- release workflow/config documentation

Required outcomes:

- Update checks, download, and install steps are validated in a controlled release path.
- Offline and no-update states remain clear.

Acceptance:

- Desktop can perform a validated update path against a real release source.

### G4. Signing Preparation

**Goal:** prepare the repository and packaging flow for Windows signing without hardcoding credentials.

Target files:

- `desktop/package.json`
- `docs/deployment/*`
- `.github/workflows/release.yml`

Required outcomes:

- Signing expectations and env variables are documented.
- Build config is ready to consume signing credentials when available.

Acceptance:

- Repository is signing-ready even if certificate provisioning is external.

### G5. Upgrade and Downgrade Safety

**Goal:** validate runtime path, sidecar, MRAG, and settings behavior across version changes.

Target files:

- `tests/contract/test_upgrade_path.py`
- `src/pyc_hermes_agent/common/runtime_paths.py`
- MRAG migration files under `src/pyc_hermes_agent/mrag_core/*`

Required outcomes:

- Upgrade path is validated for settings, sidecar, and MRAG state.
- Failure or incompatibility states are explicit.

Acceptance:

- Version transitions do not silently corrupt runtime state.

### G6. Production Release Gate Expansion

**Goal:** make release readiness measurable through automation.

Target files:

- `scripts/release_gates.py`
- `.github/workflows/ci.yml`
- `docs/deployment/Production_Release_Gates.md`
- `docs/architecture/Compatibility_Matrix.md`

Required outcomes:

- Gate matrix covers desktop packaging, install immutability, upgrade checks, and release metadata.
- Release documentation is aligned with the automated checks.

Acceptance:

- Production release readiness can be evaluated by a documented gate sequence, not only by manual judgment.

---

## 5. Execution Order

Recommended order:

1. G1 - Desktop CI Packaging Coverage
2. G2 - Clean-Machine Install Validation
3. G3 - Updater Release Flow
4. G4 - Signing Preparation
5. G5 - Upgrade and Downgrade Safety
6. G6 - Production Release Gate Expansion

---

## 6. Test Plan

Required verification:

- CI build coverage for desktop packaging
- clean-machine install smoke
- updater smoke in a controlled environment
- upgrade-path tests
- production release gate runs

Target test areas:

- `tests/contract/test_windows_packaging.py`
- `tests/contract/test_runtime_paths.py`
- `tests/contract/test_upgrade_path.py`
- `scripts/release_gates.py`
- `.github/workflows/ci.yml`

---

## 7. Risks

| Risk | Impact | Control |
|------|--------|---------|
| Packaging succeeds in CI but fails on real Windows | False release confidence | Clean-machine smoke validation |
| Updater works only in dev assumptions | Broken field updates | Validate against real release source |
| Signing preparation leaks secrets into repo | Security issue | Env-based signing setup only |
| Runtime paths regress in packaged mode | Policy violation | Runtime path and install immutability tests |

---

## 8. Exit Definition

Phase 3G is complete when:

- Desktop packaging is CI-validated.
- Install, startup, and updater paths are tested on real Windows conditions.
- Upgrade safety and path policy are covered by tests.
- Production release gates reflect actual Windows delivery requirements.

---
