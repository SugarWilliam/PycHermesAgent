# Development Checkpoint 2026-05-18

| Field | Value |
| --- | --- |
| Date | 2026-05-18 |
| Project | `PycHermesAgent` |
| Purpose | Reboot handoff and session checkpoint |
| Current branch | `main` |
| Git state at capture time | `main...origin/main [ahead 1]` |
| HEAD commit | `024b941 Advance Hermes blueprint and stabilize runtime contracts` |
| Repository status | Internal engineering preview |

## Current Context

This checkpoint captures the current working state after several Phase 1 runtime-hardening slices were completed on top of commit `024b941`.

The current working priority has been:

1. Keep the repository aligned with `docs/architecture/Phase1_Roadmap_v0.2.0.md`.
2. Continue Windows-first implementation and verification.
3. Prefer small, contract-tested slices rather than broad refactors.
4. Preserve the project boundaries in `AGENTS.md`.

## Important Environment Notes

1. Development is intentionally Windows-only for the current workstream.
2. Git is not available directly on `PATH` in the current environment.
3. Git operations are being run through `C:\Program Files\Git\git-cmd.exe`.
4. Because the workspace is on a UNC path, `git-cmd.exe` must be used with `cmd.exe` and `pushd`.

Recommended Git pattern:

```powershell
& "C:\Program Files\Git\git-cmd.exe" --command="C:\Windows\System32\cmd.exe" /c 'pushd "\\192.168.155.101\pyc\PycHermesAgent" && git status --short --branch'
```

## Current Git State

Latest visible commits at capture time:

```text
024b941 (HEAD -> main) Advance Hermes blueprint and stabilize runtime contracts
038530e (origin/main, origin/HEAD) Harden local asset and artifact validation
205f65d Add local asset and artifact foundations
```

Uncommitted files at capture time:

```text
src/pyc_hermes_agent/mrag_core/persistence.py
src/pyc_hermes_agent/sidecar_api/http_server.py
src/pyc_hermes_agent/sidecar_api/service.py
tests/contract/test_mrag_core.py
tests/contract/test_sidecar_api.py
tests/contract/test_sidecar_http.py
docs/Development_Checkpoint_2026-05-18.md
```

The current worktree is intentionally being treated as the continuation of the previous development session. These changes were not committed yet.

## What Was Completed Before This Checkpoint

Already committed in `024b941` and earlier in this working branch:

1. Hermes Phase 1 runtime baseline work was advanced.
2. Hermes session context, persistent memory, session recall, and agent-loop foundations were added.
3. Windows path-length regressions in artifact, asset, and MRAG temporary paths were fixed.
4. MetaHarness bridge degradation behavior was stabilized for unsupported legacy surfaces.
5. The repository reached a fully green contract baseline before the current uncommitted slices started.

## What Was Completed In The Current Uncommitted Slice

### Slice A: MRAG Persistence Version Markers

Files:

1. `src/pyc_hermes_agent/mrag_core/persistence.py`
2. `tests/contract/test_mrag_core.py`

Behavior added:

1. `manifest.json` now writes `manifest_version`.
2. `chunks.json` now writes `index_format_version`.
3. Legacy `chunks.json` list-only payloads still load correctly.
4. This keeps MRAG storage closer to the documented compatibility model without changing the directory split between manifests, sources, and indexes.

### Slice B: Sidecar API Version Headers

Files:

1. `src/pyc_hermes_agent/sidecar_api/service.py`
2. `src/pyc_hermes_agent/sidecar_api/http_server.py`
3. `tests/contract/test_sidecar_http.py`

Behavior added:

1. Centralized `SIDECAR_API_VERSION` constant.
2. JSON responses include `X-Pyc-Sidecar-Api-Version`.
3. SSE responses include `X-Pyc-Sidecar-Api-Version`.

### Slice C: Standardized Sidecar Transport Error Semantics

Files:

1. `src/pyc_hermes_agent/sidecar_api/service.py`
2. `src/pyc_hermes_agent/sidecar_api/http_server.py`
3. `tests/contract/test_sidecar_api.py`
4. `tests/contract/test_sidecar_http.py`

Behavior added:

1. `make_error_response()` now standardizes top-level `status: "error"` plus `ErrorEnvelope` payloads.
2. `invoke_formal_analysis()` failure now uses the same top-level error semantics as `llm/chat` and `agent/run`.
3. HTTP-generated transport errors now include:
   - `error.code`
   - `error.category`
   - `error.retryable`
   - `error.degraded`
   - `error.details.method`
   - `error.details.path`
   - `error.details.http_status`

### Slice D: Health Transition Logging

Files:

1. `src/pyc_hermes_agent/sidecar_api/http_server.py`
2. `tests/contract/test_sidecar_http.py`

Behavior added:

1. `GET /health` now emits `sidecar.health.transition` only when the top-level `status_label` changes.
2. The log includes previous and current status labels plus `degraded`.

### Slice E: Health Refresh Bug Fix

Files:

1. `src/pyc_hermes_agent/sidecar_api/service.py`
2. `tests/contract/test_sidecar_api.py`

Bug found during testing:

1. `sidecar_api` cached `HermesFacade` across requests.
2. `HermesFacade` also cached internal snapshots.
3. Result: if vendored upstream Hermes state changed during process lifetime, `get_health()` could stay stale.

Fix applied:

1. Removed cross-request `HermesFacade` caching from `sidecar_api.service`.
2. Added a regression test proving `get_health()` refreshes when upstream state changes from missing to available.

### Slice F: Request Correlation IDs In HTTP Transport

Files:

1. `src/pyc_hermes_agent/sidecar_api/http_server.py`
2. `tests/contract/test_sidecar_http.py`

Behavior added:

1. Each HTTP request now gets a stable transport-local `request_id`.
2. `http.request.started` logs include `request_id`.
3. `http.request.finished` logs include `request_id`.
4. `sidecar.health.transition` logs include `request_id`.
5. JSON responses include `X-Pyc-Request-Id`.
6. SSE responses include `X-Pyc-Request-Id`.
7. HTTP-generated error payloads include `error.details.request_id`.

## Verification Summary

Focused verification that passed during this session:

```powershell
python -m pytest tests/contract/test_mrag_core.py
python -m pytest tests/contract/test_sidecar_api.py tests/contract/test_sidecar_http.py tests/contract/test_sidecar_client.py -vv
```

Latest full contract result:

```powershell
python -m pytest tests/contract
```

Result:

```text
165 passed in 85.78s
```

## Notable Session Timeline

1. Verified that the earlier full commit already existed and that the branch was `ahead 1`.
2. Added MRAG persistence version markers and backward-compatible loading.
3. Added sidecar API version headers for JSON and SSE.
4. Standardized sidecar transport error semantics.
5. Added health transition logging.
6. Hit a failing health-transition test and traced it to stale `HermesFacade` caching.
7. Removed cross-request facade caching and added a regression test.
8. Added per-request transport `request_id` for response/log correlation.
9. Re-ran focused tests and then the full contract suite until all contracts passed.

## Recommended Next Step After Reboot

Best next implementation slice:

1. Add a minimal MRAG single-process ownership or lock guardrail so the current JSON persistence boundary is protected in code, not only in docs.

Secondary option after that:

1. Add minimal sidecar transport trace propagation rules where that materially helps streaming and loop diagnostics.

## Restart Recovery Steps

After the PC restart:

1. Open the workspace at `\\192.168.155.101\pyc\PycHermesAgent`.
2. Read this file: `docs/Development_Checkpoint_2026-05-18.md`.
3. Re-check worktree state with the UNC-safe Git command pattern.
4. Confirm the uncommitted files above are still present.
5. Resume with the MRAG single-process guardrail slice.
6. Run focused tests first, then `python -m pytest tests/contract`.

Useful commands:

```powershell
& "C:\Program Files\Git\git-cmd.exe" --command="C:\Windows\System32\cmd.exe" /c 'pushd "\\192.168.155.101\pyc\PycHermesAgent" && git status --short --branch'
```

```powershell
python -m pytest tests/contract/test_mrag_core.py -vv
```

```powershell
python -m pytest tests/contract
```

## Resume Prompt Seed

If a new session needs a compact handoff prompt, use this:

```text
Resume PycHermesAgent from docs/Development_Checkpoint_2026-05-18.md. Treat the current dirty worktree as intentional continuation work. Latest committed branch state is main ahead of origin/main by one commit at 024b941. Current uncommitted work adds MRAG persistence version markers, standardized sidecar transport errors, health transition logging, removal of stale HermesFacade caching, and per-request HTTP request_id correlation. The latest full contract suite is green at 165 passed. Next recommended slice is MRAG single-process ownership or lock guardrails.
```
