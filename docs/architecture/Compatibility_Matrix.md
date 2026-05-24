# PycHermesAgent Compatibility Matrix

**Status:** Required for release and tag decisions  
**Program boundary:** **Tranche one** (首期工程) delivery closes at **Phase 4** exit criteria — `docs/architecture/Phase3_Phase4_Productization_Roadmap_v0.3.0.md` §11 + `Phase3_Phase4_Exit_Checklist_v0.3.0.md`. Strategic evolution after that (**Phase 5**: digital teammate, gateway fork evaluation) is **`docs/architecture/Phase5_Evolution_Blueprint_v0.5.0.md`** and must **not** be treated as Phase 4 tag debt.

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
- **Phase 5-class changes** (see §6): expect **coordinated bumps** across one or more axes (`contract_version`, `sidecar_api_version`, `desktop_ipc_version`, optionally `index_format_version`) plus an ADR recorded in governance; do not increment axes piecemeal without a written migration story.

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
| **Phase 5 / gateway fork / ADR** (post–Phase 4 only) | All affected axes in §5 + **`Phase5_Evolution_Blueprint_v0.5.0.md`** linkage + governance ADR | contract tests + migration notes + desktop/sidecar consumer updates |

## 5. Current Baseline

The current repository line is **`v0.4.0`** cumulative engineering-preview workbench (**tag** aligns with package `app_version`; still **not** production / store-ready — see Gates). Production `v1.0.0` cannot be tagged until desktop packaging signing/updater, storage migration hardening, neural embeddings, and installation verification meet production criteria.

Current-truth note:

- current sidecar contract truth comes from this matrix plus validated code/tests
- historical release notes may describe what a tagged line claimed or targeted, but they are not the authoritative source for the current repository baseline

| Axis | Current value | Notes |
|------|---------------|-------|
| `app_version` | `0.4.0` (`pyc_hermes_agent.__version__`) | **v0.4.0** tag line: governance + Phase 5 charter docs, IPC MRAG benchmarks, MetaHarness IPC consistency signals, desktop formal snapshot UX, Evolution ROI receipts, sidecar/skills/evolution surfaces per `releases/v0.4.0.md` |
| `sidecar_api_version` | `0.10` | Adds session **working memory** (`AgentLoopRequest.working_memory`, `update_working_memory`; reflected in **`AgentLoopResult.working_memory`**); **`POST /knowledge-bases/{id}/materialize`** thin-ingest tagging; **`GET|POST /skills/patch-drafts`** + **`POST .../suggest-from-session`** + **`DELETE .../{uuid}`** (weak automation drafts, human-gated); append-only **`LOCALAPPDATA/.../audit/preferences.jsonl`** when preferences mutate. **`0.9` baseline retained:** `/rules/manifest` **`manifest_version: 2`** + **`runtime_profile`**; **`GET /capabilities/a2a`** + MRAG health/config surfaces |
| `contract_version` | `0.5` | `AgentLoopRequest.working_memory`, `AgentLoopRequest.update_working_memory`, `AgentLoopResult.working_memory` |
| `index_format_version` | `2` | SQLite/FTS5 artifacts and migration tooling exist via `scripts/migrate_mrag_to_sqlite.py`, but the active sidecar MRAG runtime remains JSON-backed; v1 JSON still readable for migration |
| `model_manifest_version` | `1` (asset manifest schema) | Unchanged |
| `artifact_format_version` | `1` | Unchanged |
| `skills_runtime_policy_id` | `skill-runtime-permissions-phase2-v0.3.0` | 8 builtin skills (4 prompt + 4 analysis); `SkillAuditor` tracks activation/usage; `GET /skills/audit` |
| `desktop_ipc_version` | `0.1` (preview) | electron-vite + React 18; contextBridge exposes sidecar, updater, and theme APIs; NSIS installer configured |

**GitHub Actions (Phase 4 engineering tier):** `contract-tests` (Python matrix + MRAG proofs + simulated packaging probe + `scripts/release_gates.py` with ruff+mypy); **`desktop-generic-https-feed-proof`** (Ubuntu · `desktop/tools/ci_generic_https_feed_proof.cjs` — `electron-updater` **`GenericProvider`** GET **`latest-linux.yml`** over loopback HTTPS with ephemeral self-signed cert; proves YAML/layout + resolver only, **no full app install/download**); `production-gates` (`RELEASE_GATES_PRODUCTION=1` SBOM MRAG migrate + Linux `npm run dist:dir` + `electron_dist_layout_smoke --prefer-unpacked linux`); `desktop-windows-unpacked` (Windows **`win-unpacked`** + smoke); **`desktop-windows-nsis-silent`** (dual semver NSIS + **`windows_nsis_silent_upgrade_smoke.ps1`**). Interactive **electron-updater** UI (`checking → downloading → ready`) and signed delta installs remain manual / Windows-scope — see **`docs/deployment/Windows_Install_Upgrade_Rollback_Matrix_and_Updater_Proof_v0.4.0.md`**. CI still does **not** replace Windows code signing or store-ready attestation (`Production_Release_Gates.md` honest scope).

Hermes **`create_meta_harness_tool_registry()`** default builtin tools (**non-exhaustive**, contract-tested): `formal_analysis`, **`web_search`**, **`knowledge_retrieve`** (JSON-backed `MRAGService` retrieval via `sidecar_api.services.mrag_service`; supports tests monkeypatching the module). Update this paragraph when ToolRegistry defaults change (`tests/contract/test_web_search.py`, `tests/contract/test_hermes_agent_loop.py`).

---

## 6. Tranche one vs Phase 5 (major-version posture)

| Scope | Compatibility expectation |
|-------|---------------------------|
| **Through Phase 4 (tranche one)** | Increment axes **per observable contract or disk-format change**, using §§1–4. Patch/minor semantics follow semver policy in §3. |
| **Phase 5 opens (post–tranche-one)** | Breaking or cross-cutting/runtime changes (e.g. upstream gateway adoption, memory/team-model surfaces, desktop IPC redesign) likely require **one coordinated major release story** (`app_version` major) **and** explicit bumps of every touched axis — not silent partial upgrades. |

**Authoritative charter:** `docs/architecture/Phase5_Evolution_Blueprint_v0.5.0.md`. Until Phase 5 is formally opened, **do not** add Phase-only exit criteria to Phase 4 tags based on Phase 5 items.

