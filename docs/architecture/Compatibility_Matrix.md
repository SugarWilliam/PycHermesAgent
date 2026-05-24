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
| `skills_runtime_policy_id` | `hermes_engine` / ADR | Document in matrix + roadmap when policy dict or Phase 1 scope changes | agent loop + sidecar skill listing tests |
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
| Skill runtime policy (Phase 1 dict / `start` payload) | `skills_runtime_policy_id` in §5 | agent loop + `list_skills` contract tests |
| Desktop IPC | `desktop_ipc_version` | desktop integration tests |

## 5. Current Baseline

The current repository line is **`v0.3.0`** Phase 2 complete (usable local analysis workbench with desktop shell, 15-case benchmark, 8 builtin skills, auto-updater). Production `v1.0.0` cannot be tagged until desktop packaging signing/updater, storage migration hardening, neural embeddings, and installation verification meet production criteria.

Current-truth note:

- current sidecar contract truth comes from this matrix plus validated code/tests
- historical release notes may describe what a tagged line claimed or targeted, but they are not the authoritative source for the current repository baseline

| Axis | Current value | Notes |
|------|---------------|-------|
| `app_version` | `0.3.0` (`pyc_hermes_agent.__version__`) | Phase 2 complete; desktop shell with Dify-style UI, electron-builder NSIS installer |
| `sidecar_api_version` | `0.9` | `GET /rules/manifest` **`manifest_version: 2`** adds **`runtime_profile`** (discovery engine, bundle kind, sidecar lineage). Prior: **`GET /capabilities/a2a`** (`A2A_SubAgent_Platform_Seam_v0.4.0.md`); MRAG citation anchors; **`mrag_runtime`** on `/health` + `/config`; preferences, PDF ingest, `/skills/audit`, `analysis_mode` |
| `contract_version` | `0.4` | `AgentLoopRequest.analysis_mode` added; `MetaAnalysisRequest.meta_routing` extended with `data_shape_rules`; `AgentLoopEvent.payload.analysis_card` on formal done; `Citation` adds `source_type`, `page`, `section`, and `relevance` anchors |
| `index_format_version` | `2` | SQLite/FTS5 artifacts and migration tooling exist via `scripts/migrate_mrag_to_sqlite.py`, but the active sidecar MRAG runtime remains JSON-backed; v1 JSON still readable for migration |
| `model_manifest_version` | `1` (asset manifest schema) | Unchanged |
| `artifact_format_version` | `1` | Unchanged |
| `skills_runtime_policy_id` | `skill-runtime-permissions-phase2-v0.3.0` | 8 builtin skills (4 prompt + 4 analysis); `SkillAuditor` tracks activation/usage; `GET /skills/audit` |
| `desktop_ipc_version` | `0.1` (preview) | electron-vite + React 18; contextBridge exposes sidecar, updater, and theme APIs; NSIS installer configured |

**GitHub Actions (Phase 4 engineering tier):** `contract-tests` (Python matrix + MRAG proofs + simulated packaging probe + `scripts/release_gates.py` with ruff+mypy); **`desktop-generic-https-feed-proof`** (Ubuntu · `desktop/tools/ci_generic_https_feed_proof.cjs` — `electron-updater` **`GenericProvider`** GET **`latest-linux.yml`** over loopback HTTPS with ephemeral self-signed cert; proves YAML/layout + resolver only, **no full app install/download**); `production-gates` (`RELEASE_GATES_PRODUCTION=1` SBOM MRAG migrate + Linux `npm run dist:dir` + `electron_dist_layout_smoke --prefer-unpacked linux`); `desktop-windows-unpacked` (Windows **`win-unpacked`** + smoke); **`desktop-windows-nsis-silent`** (dual semver NSIS + **`windows_nsis_silent_upgrade_smoke.ps1`**). Interactive **electron-updater** UI (`checking → downloading → ready`) and signed delta installs remain manual / Windows-scope — see **`docs/deployment/Windows_Install_Upgrade_Rollback_Matrix_and_Updater_Proof_v0.4.0.md`**. CI still does **not** replace Windows code signing or store-ready attestation (`Production_Release_Gates.md` honest scope).

Hermes **`create_meta_harness_tool_registry()`** default builtin tools (**non-exhaustive**, contract-tested): `formal_analysis`, **`web_search`**, **`knowledge_retrieve`** (JSON-backed `MRAGService` retrieval via `sidecar_api.services.mrag_service`; supports tests monkeypatching the module). Update this paragraph when ToolRegistry defaults change (`tests/contract/test_web_search.py`, `tests/contract/test_hermes_agent_loop.py`).
