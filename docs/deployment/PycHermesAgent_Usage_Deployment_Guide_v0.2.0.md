# PycHermesAgent Usage and Deployment Guide v0.2.0

**Status:** Engineering preview usage plus production release target guide

## 1. Current Supported Usage

The current repository supports local engineering-preview usage:

```bash
python -m pip install -e .
./.venv/bin/python -m pytest tests/contract
pyc-hermes-sidecar --host 127.0.0.1 --port 8765
```

If the system Python does not have `pytest`, use the project virtual environment when available:

```bash
./.venv/bin/python -m pytest tests/contract
```

## 2. Current Deployment Boundary

Supported today:

- editable local Python install,
- in-process sidecar calls,
- localhost HTTP sidecar,
- minimal SSE for chat and AgentLoop,
- local MRAG JSON persistence,
- local asset/artifact helper modules.

Not production-supported yet:

- Electron desktop installation,
- production service deployment,
- exposed network sidecar,
- production MRAG database,
- packaged model download workflow,
- signed installer and upgrade path.

## 3. Local Runtime Paths

The product must respect platform storage boundaries:

- Install directory: read-only.
- Configuration: roaming application data.
- Logs, caches, indexes, downloads, models, artifacts: local application data.
- Temporary downloads: staging directory with checksum validation and promotion.

No runtime feature may write mutable state into the install directory.

## 4. Sidecar Operation

The sidecar is intended for localhost use by the desktop shell or local clients.

Production hardening requirements before broader deployment:

- stable request ID and trace propagation,
- structured error envelope coverage,
- health transition logging,
- no unauthenticated public network exposure,
- smoke tests for health and non-network paths.

## 5. Release Process

Cursor is conditionally authorized to push, tag, and prepare release output only when governance gates pass.

Required pre-release checks:

```bash
./.venv/bin/python -m pytest tests/contract
```

Additional release checks:

- classify `git status`,
- inspect `git diff`,
- confirm no secrets or local runtime assets are staged,
- update compatibility matrix,
- update release notes,
- run scope-specific smoke tests,
- confirm no Blocker/High risks remain.

## 6. Tag and Release Commands

These commands are allowed only after gates pass and no destructive git action is needed:

```bash
git status
git diff --stat
git add <verified-files>
git commit -m "<verified message>"
git push origin HEAD
git tag vX.Y.Z-preview.N
git push origin vX.Y.Z-preview.N
```

Production tags use `vX.Y.Z` only when production gates pass. Preview and RC tags must not be described as production releases.

## 7. Failure Handling

Stop and report instead of releasing when:

- tests fail,
- status includes unknown changes,
- secrets are detected,
- release would require force push,
- version/tag policy is unclear,
- docs and compatibility matrix are stale,
- any production claim is unsupported by implemented and tested behavior.

## 8. Desktop Deployment Target

Electron packaging must not begin until sidecar contracts, MRAG ownership, runtime paths, asset/artifact contracts, and release gate automation are stable. Desktop E2E tests remain last in the test priority order.
