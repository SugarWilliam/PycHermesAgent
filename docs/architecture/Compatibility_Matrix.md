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
| `sidecar_api_version` | `0.7` | Added: richer MRAG citation payload fields (`source_type`, `page`, `section`, `relevance`) on search responses; `/health` and `/config` expose explicit `mrag_runtime`; plus `GET/PUT/DELETE /preferences`, `POST /kb/.../ingest-pdf`, `GET /skills/audit`, health state machine with component probes, `analysis_mode` on agent requests |
| `contract_version` | `0.4` | `AgentLoopRequest.analysis_mode` added; `MetaAnalysisRequest.meta_routing` extended with `data_shape_rules`; `AgentLoopEvent.payload.analysis_card` on formal done; `Citation` adds `source_type`, `page`, `section`, and `relevance` anchors |
| `index_format_version` | `2` | SQLite/FTS5 artifacts and migration tooling exist via `scripts/migrate_mrag_to_sqlite.py`, but the active sidecar MRAG runtime remains JSON-backed; v1 JSON still readable for migration |
| `model_manifest_version` | `1` (asset manifest schema) | Unchanged |
| `artifact_format_version` | `1` | Unchanged |
| `skills_runtime_policy_id` | `skill-runtime-permissions-phase2-v0.3.0` | 8 builtin skills (4 prompt + 4 analysis); `SkillAuditor` tracks activation/usage; `GET /skills/audit` |
| `desktop_ipc_version` | `0.1` (preview) | electron-vite + React 18; contextBridge exposes sidecar, updater, and theme APIs; NSIS installer configured |

**GitHub Actions (Phase 4 engineering tier):** `contract-tests` (Python matrix + MRAG proofs + simulated packaging probe + `scripts/release_gates.py` with ruff+mypy), `production-gates` (`RELEASE_GATES_PRODUCTION=1` SBOM MRAG migrate + Linux `npm run dist:dir` + `electron_dist_layout_smoke --prefer-unpacked linux`), `desktop-windows-unpacked` (Windows **`win-unpacked`** + same smoke with `--prefer-unpacked win`), and **`desktop-windows-nsis-silent`** (`npm run dist:win` NSIS + **`windows_nsis_silent_upgrade_smoke.ps1`** silent install loop). This does **not** replace code signing, **electron-updater** feed proofs, or store-ready attestation (`Production_Release_Gates.md` Honest scope).

Hermes **`create_meta_harness_tool_registry()`** default builtin tools (**non-exhaustive**, contract-tested): `formal_analysis`, **`web_search`**, **`knowledge_retrieve`** (JSON-backed `MRAGService` retrieval via `sidecar_api.services.mrag_service`; supports tests monkeypatching the module). Update this paragraph when ToolRegistry defaults change (`tests/contract/test_web_search.py`, `tests/contract/test_hermes_agent_loop.py`).
