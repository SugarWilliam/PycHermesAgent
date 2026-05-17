# PycHermesAgent Compatibility Matrix

**Status:** Required for release and tag decisions

## 1. Version Axes

| Axis | Owner | Current Policy | Release Impact |
|------|-------|----------------|----------------|
| `app_version` | package/release | Semantic version or preview suffix | tag and release notes |
| `sidecar_api_version` | `sidecar_api` | Increment on route or payload contract changes | client compatibility |
| `contract_version` | `contracts` | Increment on dataclass/schema changes | tests and migration notes |
| `model_manifest_version` | `asset_manager` | Increment on asset manifest changes | model install compatibility |
| `index_format_version` | `mrag_core` | Increment on index layout changes | migration or rebuild required |
| `artifact_format_version` | `artifact_engine` | Increment on artifact metadata changes | artifact consumers |
| `desktop_ipc_version` | desktop shell | Planned | desktop/sidecar compatibility |

## 2. Tag Classes

| Tag | Meaning | Allowed Automation |
|-----|---------|--------------------|
| `vX.Y.Z-preview.N` | Engineering preview checkpoint | Cursor may create after preview gates pass |
| `vX.Y.Z-rc.N` | Release candidate | Cursor may create after RC gates pass |
| `vX.Y.Z` | Production release | Cursor may create only after production gates pass |

## 3. Compatibility Rules

- Patch versions must not break sidecar API payloads.
- Minor versions may add fields and routes, but must keep documented defaults.
- Major versions may remove or break compatibility only with migration notes.
- MRAG index format changes require migration or explicit rebuild behavior.
- Asset manifest changes require checksum and promotion compatibility tests.
- Artifact format changes require consumer-facing release notes.

## 4. Release Matrix Checklist

Before a tag is created, update this table when applicable:

| Change Type | Required Update | Required Test |
|-------------|-----------------|---------------|
| Sidecar route/payload | `sidecar_api_version` | sidecar client + HTTP tests |
| Contract dataclass/schema | `contract_version` | contract tests |
| MRAG persistence/index | `index_format_version` | restart + migration/rebuild tests |
| Asset manifest/promotion | `model_manifest_version` | asset manager tests |
| Artifact metadata | `artifact_format_version` | artifact engine tests |
| Desktop IPC | `desktop_ipc_version` | desktop integration tests |

## 5. Current Baseline

The current repository line is `v0.2.0` engineering preview. Production `v1.0.0` cannot be tagged until desktop packaging, release gates, storage migration, and installation verification exist.

| Axis | Current value | Notes |
|------|---------------|-------|
| `app_version` | `0.2.0` (`pyc_hermes_agent.__version__`) | Engineering preview |
| `sidecar_api_version` | `0.2` | Adds `GET /assets`, `GET /artifacts`, `GET /artifacts/task/{task_id}`; extends `/skills` items with `runtime` metadata |
| `contract_version` | (implicit `0.x`; bump when dataclasses break) | No bump in this change set |
| `index_format_version` | `1` (MRAG manifest) | See `docs/design/MRAG_Index_Strategy_Decision_v0.2.0.md` |
| `model_manifest_version` | `1` (asset manifest schema) | Unchanged |
| `artifact_format_version` | `1` | Unchanged |
| `desktop_ipc_version` | n/a | Desktop shell not shipped |
