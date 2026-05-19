# PycHermesAgent Phase 3 to Phase 4 Productization Roadmap v0.3.0

**Status:** Proposed execution plan
**Authority:** `docs/Project_Development_and_Release_Governance.md`
**Builds on:** `docs/architecture/Phase2_Toward_GA_v0.2.1.md`
**Phase target:** From "usable local analysis workbench" to "extensible Windows-first local agent product with broad document intelligence, network grounding, and release-grade desktop delivery"
**Parallel tracks:** Real product integration + Retrieval expansion + Authoring capabilities + Extensibility hardening + Release hardening

---

## 0. Scope and Outcome

Phase 2 delivered a usable local analysis workbench:

- Electron desktop shell with Dify-style three-column layout
- SSE chat streaming
- Markdown / Mermaid / ECharts / KaTeX / Shiki rendering
- SQLite/FTS5 MRAG
- PDF ingest
- builtin skills
- GitHub Copilot-style LLM provider support
- MetaFramework-backed formal analysis path

Phase 3 to Phase 4 closes the gap between that engineering preview and the original product direction:

1. Real desktop-to-sidecar runtime integration on Windows
2. Real-time network search
3. Broader multimodal / multi-format MRAG ingestion
4. Stronger customer-loadable skills and rules runtime
5. PPT / XLSX artifact authoring
6. Better grounded retrieval, evidence-chain verification, and MetaFramework evidence flow
7. Release-grade Windows installer, updater, and validation

---

## 1. Locked Architecture Rules

The following remain mandatory:

- Formal analysis must continue to enter via `MetaFramework.execute()`.
- `hermes_engine` remains the product-owned runtime.
- `meta_harness` remains a methodology / quality harness, not the general runtime.
- `llm_gateway` remains the only provider/model/auth boundary.
- Provider-native SDK objects must not cross out of `llm_gateway`.
- `mrag_core` owns ingestion, parsing, chunking, indexing, retrieval, reranking, and citation packaging only.
- `mrag_core` must not become a mixed store for logs, chat memory, assets, or exported artifacts.
- Install directory remains read-only.
- Desktop never writes mutable runtime data into install directory.
- Skills remain explicit activation only unless a future permissions model is approved.

---

## 2. Exit Criteria

Phase 3 is complete when:

- Desktop launches and connects to a real local sidecar without mock infrastructure.
- Real-time network search is available as a tool and visible in desktop evidence flows.
- MRAG supports at least `text`, `url`, `html`, `pdf`, `docx`, `xlsx`, `pptx`, and `image` ingestion.
- Customer-loaded skills and rules participate in the runtime through explicit, auditable activation.
- Basic PPT and XLSX generation is available as exported artifacts.
- Hybrid retrieval is stronger than lexical-only on a defined benchmark subset.

Phase 4 is complete when:

- Windows desktop packaging, upgrade, and updater flows are validated on clean machines.
- CI builds and verifies Python sidecar + desktop package artifacts.
- Release gates cover packaging, install-time immutability, upgrade checks, and desktop smoke validation.
- The product is positioned for release candidates instead of engineering preview-only use.

---

## 3. Capability Gap vs Original Product Goal

| Area | Phase 2 status | Gap to close |
|------|----------------|--------------|
| Desktop UX | Usable preview | Real sidecar launch/integration, install validation |
| GitHub Copilot | Supported in gateway | Real end-user configuration and desktop settings validation |
| Hermes inheritance | Read-only bridge + product runtime | Better continuity with Hermes memory/session behaviors without collapsing boundaries |
| MRAG | SQLite/FTS5 + PDF + file/url text | Multi-format ingestion, stronger citation fidelity, better semantic retrieval, and stronger multi-source evidence convergence |
| Network grounding | Not implemented | Real-time web search tool and evidence path |
| Skills | Builtins + `.opencode/skills` metadata and controlled context binding | User-loadable runtime activation, UI, audit, priority model, and agent-authored skills from user request or long-term usage patterns |
| Rules | Discovery only | Runtime prompt assembly and precedence enforcement |
| Authoring | Artifact engine foundation only | PPT/XLSX creation workflows |
| Release | Preview-grade | Installer, upgrade, updater, CI, signing preparation |

---

## 4. Workstreams

### Track A: Real Desktop Integration

**Goal:** Convert the desktop from validated preview shell to a real Windows product shell backed by the Python sidecar.

| ID | Task | Detail | Acceptance |
|----|------|--------|------------|
| A1 | Real sidecar startup contract | Desktop launches or attaches to local sidecar with stable port/path policy | Desktop can connect to real sidecar without mock server |
| A2 | Sidecar URL unification | Remove mismatched defaults between desktop and sidecar runtime | Single authoritative sidecar URL policy |
| A3 | Desktop degraded-state UX | Health failures, sidecar unavailable, startup timeout, port conflict surfaced clearly | Friendly UI state replaces silent failure |
| A4 | Real SSE integration validation | Validate chat, formal mode, analysis cards, tool calls, cancellation | Real end-to-end chat flow passes |
| A5 | Packaging smoke | `electron-builder --dir` and NSIS output verified locally | Desktop package starts and reaches health-ready UI |
| A6 | Install-path policy validation | Installed app respects `%APPDATA%` / `%LOCALAPPDATA%` runtime paths | No mutable runtime writes under install dir |

### Track B: Real-Time Network Search

**Goal:** Add internet-grounded retrieval without breaking evidence boundaries.

| ID | Task | Detail | Acceptance |
|----|------|--------|------------|
| B1 | Search provider abstraction | Introduce provider-neutral web search interface under product runtime/tooling | Search backend swappable without UI changes |
| B2 | Web search tool | Add a runtime tool for network search usable by AgentLoop | Tool callable in chat and formal modes |
| B3 | Evidence normalization | Search results normalized to title / URL / snippet / timestamp / source metadata | Desktop renders them uniformly |
| B4 | Citation integration | Search results appear in evidence/citation panel | User can inspect network-grounded evidence |
| B5 | Formal mode grounding | Formal analysis can consume network evidence without bypassing `MetaFramework.execute()` | Formal mode preserves evidence boundary |
| B6 | Failure handling | Offline, rate-limit, provider error, empty results handled cleanly | Search failure states do not break chat loop |

### Track C: Multi-Format MRAG Expansion

**Goal:** Move from text/PDF retrieval toward the multi-format product direction.

| ID | Task | Format / scope | Acceptance |
|----|------|----------------|------------|
| C1 | HTML ingest | Raw HTML and cleaned content extraction | Title, source URI, body text preserved |
| C2 | DOCX ingest | Paragraphs, headings, table text | Citations preserve section/document provenance |
| C3 | XLSX ingest | Workbook/sheet/table/cell text extraction | Citations identify workbook + sheet |
| C4 | PPTX ingest | Slide title/body/notes extraction | Citations identify slide number |
| C5 | Image ingest | OCR-first extraction and source metadata | Searchable text from supported image files |
| C6 | Unified parser registry | Format dispatch under `mrag_core` | Ingestion path stays centralized |
| C7 | Rich citation metadata | Page/sheet/slide/section/source-type all preserved | Desktop citation panel shows origin clearly |
| C8 | Compatibility & migration | Index and manifest version rules updated if storage payload changes | Compatibility matrix updated and tested |

### Track D: Skills and Rules Runtime Hardening

**Goal:** Make extension surfaces truly user-loadable and auditable.

| ID | Task | Detail | Acceptance |
|----|------|--------|------------|
| D1 | User skill load path | Support project-level and user-level skill directories | User can add skills without code changes |
| D2 | Builtin vs user skill separation | Distinguish product-owned and user-owned skill sources | UI and runtime can show provenance |
| D3 | Runtime skill assembly | Active skills contribute controlled system context in deterministic order | Activation materially affects runtime output |
| D4 | Rule precedence model | `system > project > user > skill` or equivalent documented ordering | Prompt assembly is deterministic and testable |
| D5 | Audit trail enhancement | Record which rules and skills were active for a run | Sidecar and desktop can inspect audit state |
| D6 | User-requested skill authoring | Agent can generate a valid `SKILL.md` from explicit user request and save it into project/user skill directories with audit metadata | User can ask the agent to create a reusable skill without manual file authoring |
| D7 | Preference/habit-derived skill synthesis | Agent can propose or generate personal skills from recurring prompts, preferences, and long-term usage patterns | Repeated behavior can be promoted into reusable skills |
| D8 | Desktop management UI | User can list/activate/deactivate/reload skills and inspect rule sources | Extension management works from desktop |
| D9 | Permissions deferral integrity | Keep script execution disabled until approved policy exists | No silent execution path appears |

### Track E: PPT and XLSX Authoring

**Goal:** Add product-grade artifact creation for common business outputs.

| ID | Task | Detail | Acceptance |
|----|------|--------|------------|
| E1 | Artifact authoring API | Extend artifact generation interfaces for document outputs | API supports typed export requests |
| E2 | PPTX generator MVP | Title, agenda, content, table, chart slides | Agent can export a basic presentation |
| E3 | XLSX generator MVP | Tables, multiple sheets, summaries, chart sheet | Agent can export a basic workbook |
| E4 | Template model | Product-owned output templates for consistent visual quality | Generated files have readable styling |
| E5 | Desktop artifact UX | Artifact list and open/export entry points | Generated files visible from desktop |
| E6 | Prompt-to-artifact flow | Agent can transform structured outputs into exportable files | User asks for PPT/XLSX and receives artifact |

### Track F: Retrieval and MetaFramework Strengthening

**Goal:** Improve grounding quality and evidence-aware formal analysis.

| ID | Task | Detail | Acceptance |
|----|------|--------|------------|
| F1 | Real embeddings layer | Introduce actual semantic embeddings path | Semantic retrieval available |
| F2 | Hybrid retrieval tuning | Support lexical / semantic / hybrid modes | Hybrid improves over lexical baseline |
| F3 | Retrieval benchmark expansion | Compare quality on representative document tasks | Benchmark artifacts reproducible |
| F4 | Evidence-chain verification | Normalize multi-source evidence, detect unresolved conflicts, and preserve edge-level traceability for multi-hop conclusions | Multi-source conclusions remain inspectable and conflict-aware |
| F5 | Logic and temporal consistency checks | Detect circular reasoning, causal reversal, scope drift, missing chain links, and timeline contradictions | Weak logic paths are surfaced as risks or degraded conclusions |
| F6 | Formal evidence package upgrade | Feed retrieval evidence into `MetaFramework.execute()` in structured, source-aware form | Formal results show evidence grounding clearly |
| F7 | Degraded evidence policy | Explicitly mark low-evidence, conflict-heavy, or partial-grounding outputs | Users can distinguish weak grounding |

### Track G: Windows Release Hardening

**Goal:** Make the desktop releaseable, installable, and supportable.

| ID | Task | Detail | Acceptance |
|----|------|--------|------------|
| G1 | Desktop CI build | Build desktop artifacts in CI | Reproducible desktop build job exists |
| G2 | Clean-machine smoke | Validate install/startup on clean Windows environment | Installer tested beyond dev machine |
| G3 | Updater release path | Connect packaged updater flow to real release process | Update check/download/install path validated |
| G4 | Signing preparation | Prepare config and documented process for Authenticode signing | Signing slot is ready even if certificate comes later |
| G5 | Upgrade/downgrade validation | Runtime path, sidecar, settings, and MRAG migrations behave safely | Upgrade path documented and tested |
| G6 | Production release gates | Extend `scripts/release_gates.py` and CI for desktop/release checks | Production gate matrix enforced |

---

## 5. Delivery Order

Recommended execution order:

1. Track A: Real Desktop Integration
2. Track B: Real-Time Network Search
3. Track C: Multi-Format MRAG Expansion
4. Track D: Skills and Rules Runtime Hardening
5. Track E: PPT and XLSX Authoring
6. Track F: Retrieval and MetaFramework Strengthening
7. Track G: Windows Release Hardening

Rationale:

- The desktop must first be real and stable.
- Network grounding and broader ingest close the biggest product gaps.
- Skills/rules and authoring improve extensibility and business usability after the core data path is stronger.
- Release hardening should follow once major product behavior stabilizes.

---

## 6. Required File Areas by Track

### Track A

- `desktop/electron/main.js`
- `desktop/electron/preload.js`
- `desktop/src/services/sidecarClient.js`
- `desktop/src/store/chatStore.js`
- `desktop/src/components/layout/*`
- `desktop/src/components/settings/*`
- `src/pyc_hermes_agent/sidecar_api/http_server.py`
- `src/pyc_hermes_agent/common/runtime_paths.py`
- `packaging/windows/*`

### Track B

- `src/pyc_hermes_agent/hermes_engine/tools/*`
- `src/pyc_hermes_agent/hermes_engine/tool_registry.py`
- `src/pyc_hermes_agent/hermes_engine/agent_loop.py`
- `src/pyc_hermes_agent/sidecar_api/services/*`
- `desktop/src/components/context/*`

### Track C

- `src/pyc_hermes_agent/mrag_core/*`
- `src/pyc_hermes_agent/sidecar_api/services/mrag_service.py`
- `src/pyc_hermes_agent/sidecar_api/http_server.py`
- `desktop/src/components/context/CitationList.jsx`

### Track D

- `src/pyc_hermes_agent/llm_gateway/skills.py`
- `src/pyc_hermes_agent/llm_gateway/rules.py`
- `src/pyc_hermes_agent/hermes_engine/skill_context.py`
- `src/pyc_hermes_agent/hermes_engine/skills/*`
- `src/pyc_hermes_agent/hermes_engine/memory.py`
- `src/pyc_hermes_agent/sidecar_api/services/skill_service.py`
- `desktop/src/components/skills/*`

### Track E

- `src/pyc_hermes_agent/artifact_engine/*`
- `src/pyc_hermes_agent/sidecar_api/services/common.py`
- `src/pyc_hermes_agent/sidecar_api/http_server.py`
- `desktop/src/components/context/*`

### Track F

- `src/pyc_hermes_agent/mrag_core/*`
- `src/pyc_hermes_agent/meta_harness/*`
- `src/pyc_hermes_agent/sidecar_api/services/chat_service.py`
- `benchmarks/meta_harness/*`

### Track G

- `desktop/package.json`
- `.github/workflows/*`
- `scripts/release_gates.py`
- `docs/deployment/*`
- `docs/releases/*`

---

## 7. Testing Requirements

### Minimum per-track verification

- Track A:
  - desktop build succeeds
  - desktop launch + sidecar health smoke
  - real SSE chat path
  - install-dir immutability checks

- Track B:
  - tool contract tests
  - provider failure tests
  - evidence rendering tests
  - formal mode grounding tests

- Track C:
  - per-format parser tests
  - ingestion contract tests
  - citation fidelity tests
  - restart/rebuild tests if index layout changes

- Track D:
  - skill/rule discovery tests
  - activation ordering tests
  - audit tests
  - desktop extension management tests

- Track E:
  - artifact generation tests
  - file-openability sanity checks
  - desktop artifact listing tests

- Track F:
  - retrieval benchmark tests
  - semantic/hybrid mode correctness tests
  - MetaFramework evidence integration tests

- Track G:
  - CI package build
  - installer smoke
  - update path smoke
  - release gate automation

### Ongoing mandatory gate

At every milestone:

- contract tests first
- smoke tests second
- compatibility / migration checks third
- desktop integration tests after core contracts are stable

---

## 8. Risks and Controls

| Risk | Impact | Control |
|------|--------|---------|
| Desktop and sidecar drift again on ports/paths | Broken runtime integration | Single authoritative sidecar config path |
| MRAG parser sprawl breaks boundaries | Architecture erosion | Central parser registry inside `mrag_core` only |
| Network search pollutes formal analysis | Evidence/claim boundary violation | Formal mode continues to route through `MetaFramework.execute()` |
| User skills become unsafe execution surface | Security and behavior instability | Keep script execution disabled pending permissions model |
| Office authoring grows into unbounded templating scope | Delivery delay | Start with narrow MVP export templates |
| Release work starts too early | Churn and rework | Do packaging hardening after major product capabilities stabilize |

---

## 9. Compatibility Matrix Implications

The following version axes are expected to change during Phase 3 to Phase 4:

- `sidecar_api_version`
- `contract_version`
- `index_format_version` if richer citation or embedding storage changes disk layout
- `artifact_format_version` for PPT/XLSX metadata
- `skills_runtime_policy_id` if user-loadable runtime semantics change
- `desktop_ipc_version` once desktop-side APIs stabilize

Every such change must update:

- `docs/architecture/Compatibility_Matrix.md`
- relevant contract tests
- release notes / migration notes where applicable

---

## 10. Definition of Success

At the end of Phase 4, PycHermesAgent should be credibly describable as:

- a Windows-first desktop agent product
- with local-first grounded retrieval
- with GitHub Copilot-compatible LLM access
- with MetaFramework-backed formal analysis
- with user-loadable skills and rules
- with business-output artifact generation
- and with a release-grade installation and update path

It must still preserve the core project constraints:

- product-owned runtime
- provider isolation
- evidence separation
- explicit skill activation
- read-only install directory
- `MetaFramework.execute()` as the formal analysis entry point

---
