# Phase 3G1 - Windows Installer and Updater Plan v0.3.0

**Status:** Proposed execution plan
**Authority:** `docs/Project_Development_and_Release_Governance.md`
**Parent roadmap:** `docs/architecture/Phase3G_Windows_Release_Hardening_Plan_v0.3.0.md`
**Goal:** Define the concrete implementation path for Windows installer validation, updater release flow, and packaging-policy enforcement for the desktop + sidecar product.

---

## 1. Scope

Phase 3G1 narrows the broader release-hardening work into desktop delivery mechanics.

In scope:

- NSIS installer packaging validation
- packaged sidecar resource expectations
- clean-machine smoke checklist
- updater behavior and release-source validation
- packaging policy and install immutability checks

Out of scope:

- full code-signing certificate procurement
- store distribution channels
- non-Windows package formats as primary target

---

## 2. Current Baseline

Current completed baseline includes:

- `desktop/package.json` with `electron-builder` NSIS config and GitHub publish config
- updater wiring in `desktop/electron/main.js`
- preview packaging launcher in `packaging/windows/Run-SidecarPreview.ps1`
- packaging probe tests in `tests/contract/test_windows_packaging.py`
- release gate support in `scripts/release_gates.py`

Current gap:

- no completed clean-Windows installer validation loop
- no fully validated updater release path
- no dedicated execution document for installer/updater hardening

---

## 3. Architecture Rules

- Install directory remains read-only.
- Packaged desktop must not hide runtime-path violations.
- Updater integration must not bypass release gate checks.
- Sidecar packaging must respect existing runtime ownership boundaries.

---

## 4. Workstreams

### W1. Installer Packaging Contract

Target files:

- `desktop/package.json`
- `packaging/windows/*`
- `docs/deployment/*`

Required outcomes:

- Installer layout and bundled sidecar resources are explicitly documented.
- Packaged resource expectations are testable.

### W2. Clean-Machine Smoke Procedure

Target files:

- `docs/deployment/*`
- new smoke checklist doc if needed
- `tests/contract/test_windows_packaging.py`

Required outcomes:

- Reproducible install/startup checklist for a fresh Windows machine.
- Health, sidecar connection, and runtime-path verification included.

### W3. Updater Operational Flow

Target files:

- `desktop/electron/main.js`
- `desktop/src/components/settings/UpdateNotification.jsx`
- `.github/workflows/release.yml`

Required outcomes:

- Update check, download, and install flows are documented against a real release source.
- Failure and no-update states remain user-readable.

### W4. Packaging Policy Enforcement

Target files:

- `packaging/windows/README.md`
- `src/pyc_hermes_agent/packaging/*`
- `tests/contract/test_windows_packaging.py`
- `tests/contract/test_runtime_paths.py`

Required outcomes:

- Installer assumptions align with packaging policy tests.
- Runtime write locations remain outside install directory.

### W5. CI and Release Gate Alignment

Target files:

- `.github/workflows/ci.yml`
- `.github/workflows/release.yml`
- `scripts/release_gates.py`

Required outcomes:

- Installer/updater validation expectations are reflected in CI and release gates.

---

## 5. Test Plan

Target tests:

- `tests/contract/test_windows_packaging.py`
- `tests/contract/test_runtime_paths.py`
- `tests/contract/test_upgrade_path.py`

Required verification:

- packaged app respects runtime-path policy
- installer flow is documented and repeatable
- updater flow is validated in a controlled release path

---

## 6. Risks

| Risk | Impact | Control |
|------|--------|---------|
| Installer assumptions drift from packaging policy | Broken packaged runtime | Keep docs/tests/gates aligned |
| Updater works only in dev assumptions | Broken field update path | Validate against real release source |
| Packaged sidecar resources are incomplete | Launch failure after install | Explicit resource contract and smoke checks |

---

## 7. Exit Definition

Phase 3G1 is complete when:

- Installer packaging assumptions are documented and validated.
- Clean-machine smoke procedure is defined and usable.
- Updater flow is operationally specified and aligned with release gates.

---
