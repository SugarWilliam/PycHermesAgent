# PycHermesAgent Execution Blueprint

| Field | Value |
| --- | --- |
| Date | 2026-05-16 |
| Version | v0.2.0 |
| Author | 彭耀成 |
| Status | Long-Horizon Execution and Acceptance Blueprint |

## Purpose

This document is the long-horizon execution blueprint for evolving `PycHermesAgent` from an internal engineering preview into a releasable Windows desktop agent product.

It exists to align development around five non-negotiable product goals:

1. Releasable
2. Production-grade
3. Extensible
4. Robust
5. Strong Agent capability

This blueprint is intended to guide:

1. Development sequencing
2. Cross-module design decisions
3. Milestone acceptance
4. Release gating
5. Long-term maintenance

## Product Intent

`PycHermesAgent` is intended to become a Windows desktop agent product that:

1. Inherits Hermes learning and memory strengths through controlled integration
2. Integrates GitHub Copilot as a first-class LLM runtime path
3. Treats `pyc-MetaFramework` as a core analysis and judgment capability
4. Provides local-first MRAG with multimodal ingestion and evidence grounding
5. Supports user-loadable skills and rules
6. Produces strong, readable, well-rendered outputs and artifacts
7. Ships as a stable, supportable Windows desktop product

## Product-Level Success Criteria

The product should not be considered delivered until all of the following are true:

1. A Windows desktop user can install, launch, and use the application without developer intervention.
2. The sidecar can survive normal restarts without losing user sessions, user-configured skills/rules, and knowledge-base state.
3. At least one real GitHub Copilot runtime path is available through `llm_gateway`.
4. Hermes-derived session and memory capabilities are integrated without collapsing the existing layer boundaries.
5. Formal analysis continues to enter only through `MetaFramework.execute()`.
6. Skills and rules can be loaded by end users through supported product workflows.
7. Knowledge retrieval preserves citations and source references.
8. Artifact creation includes at least structured outputs plus presentation-grade outputs.
9. Release validation includes desktop, sidecar, persistence, upgrade, and stability coverage.

## Hard Design Constraints

These constraints are binding across all workstreams.

### Architectural Boundaries

- Formal analysis must go through `MetaFramework.execute()`.
- `hermes_engine` owns orchestration, session state, memory integration, and tool loop behavior.
- `meta_harness` must not own provider authentication, renderer state, or general orchestration runtime.
- `llm_gateway` is the only LLM execution boundary and must not leak provider-native objects upward.
- `mrag_core` owns ingestion, indexing, retrieval, rerank, and evidence packaging.
- `sidecar_api` exposes product-facing contracts; it does not own orchestration policy.

### Packaging and Storage Boundaries

- The install directory must remain read-only.
- Configuration lives in `%APPDATA%`.
- Logs, cache, downloads, indexes, models, sessions, and artifacts live in `%LOCALAPPDATA%`.
- Models must use staging-directory promotion with checksum validation.
- MRAG indexes, sources, and artifacts must remain physically separate.

### Product Integrity Boundaries

- The repository must not claim production readiness before the release gates in this blueprint are satisfied.
- Compatibility with `opencode.json/jsonc`, `AGENTS.md`, and `.opencode/skills/*/SKILL.md` must remain intentional and documented.
- Predictive outputs must not be presented as intervention-grade causal claims.

## Functional Anchors

The following anchors define what the product must become. They are not optional nice-to-haves.

### Anchor A: Hermes-Derived Learning and Memory

The product must retain the core value of Hermes-style learning and memory through controlled integration.

Required outcomes:

1. Session continuity across restarts
2. Cross-session recall and search
3. User preference memory distinct from task or workspace memory
4. Prompt-safe memory injection rules
5. Future-compatible external memory provider abstraction

Recommended implementation posture:

1. Deeply integrate Hermes session and memory data-layer concepts
2. Rebuild orchestration in `hermes_engine`
3. Do not embed upstream `run_agent.py` as the product runtime

### Anchor B: GitHub Copilot as a First-Class LLM Path

The product must support GitHub Copilot as a real runtime, not only as catalog metadata.

Required outcomes:

1. `github-copilot/<model>` identifiers remain first-class
2. `llm_gateway` can execute at least one real Copilot path
3. Authentication, token refresh, provider headers, and model routing stay inside `llm_gateway`
4. Product layers above `llm_gateway` only consume normalized request/response contracts

Recommended sequencing:

1. First: direct Copilot API integration
2. Second: `copilot-acp` external-process compatibility
3. Later: broader editor or ACP ecosystem interop if justified

### Anchor C: MetaFramework as Base Capability

`pyc-MetaFramework` must remain a core product differentiator rather than a side tool.

Required outcomes:

1. `formal_analysis` remains a builtin callable capability
2. Agent runtime can intentionally invoke methodology review when needed
3. Degraded state, assumptions, evidence grade, risks, and recommendations remain visible in outputs
4. Agent stop or downgrade behavior can use `MetaFramework` outputs where appropriate

### Anchor D: Multimodal MRAG

The product must move beyond text-only MRAG.

Required outcomes:

1. `markdown`, `text`, `html`, and `url` support remain stable
2. `pdf`, `docx`, `xlsx`, `pptx`, and images become supported ingestion targets
3. Citation grounding remains preserved across all supported types
4. Retrieval contracts stay stable even as parsers evolve

### Anchor E: User-Loadable Skills and Rules

The product must support user-controlled extensibility.

Required outcomes:

1. Rules can be discovered, loaded, and applied to runtime prompt assembly
2. Skills can be discovered, inspected, explicitly activated, and traced in results
3. Product consumers can distinguish between metadata discovery and active runtime use
4. Global user-owned and workspace-owned instruction assets can coexist under defined precedence rules

### Anchor F: Windows Desktop Product Quality

The product must be a real Windows desktop application rather than a Python preview with future UI ambitions.

Required outcomes:

1. Electron desktop shell
2. Sidecar lifecycle management
3. Knowledge and analysis workflow UI
4. Skills and rules management UI
5. Settings for providers, models, runtime paths, and diagnostics
6. Install, upgrade, uninstall, and crash-recovery behavior appropriate for end users

### Anchor G: High-Quality Output and Artifact Production

The product must produce readable and useful outputs, not only raw JSON or console text.

Required outcomes:

1. Structured result export
2. Rich `markdown` and `html` rendering
3. `xlsx` output generation
4. `pptx` output generation
5. Artifact provenance and checksum metadata

## Cross-Cutting Execution Workstreams

Development should proceed through five parallel workstreams rather than a single feature queue.

### Workstream 1: Agent Core

Scope:

1. `hermes_engine` runtime ownership
2. Session persistence and memory
3. Tool loop and planning behavior
4. Recovery and retry policy
5. MetaFramework runtime integration

Primary target:

- Deliver a strong local Agent runtime that can sustain long-running task sessions and structured analysis work.

### Workstream 2: Production Foundation

Scope:

1. Storage durability model
2. Migrations and compatibility markers
3. Concurrency and locking rules
4. Health semantics and diagnostics
5. Structured logging and crash visibility
6. Secure token and configuration handling

Primary target:

- Prevent the codebase from becoming feature-rich but operationally fragile.

### Workstream 3: Extensibility Platform

Scope:

1. Skills lifecycle
2. Rules lifecycle
3. Provider adapter contracts
4. Artifact contracts
5. Extension compatibility and versioning
6. Permission and trust boundaries

Primary target:

- Make extensibility explicit, maintainable, and safe rather than implicit and ad hoc.

### Workstream 4: Knowledge and Artifact System

Scope:

1. Multimodal MRAG
2. Evidence preservation
3. Artifact export and rendering
4. Presentation-quality output generation

Primary target:

- Support grounded knowledge work and high-quality deliverables.

### Workstream 5: Desktop Product and Release Engineering

Scope:

1. Electron shell
2. Sidecar lifecycle supervision
3. Desktop UX
4. Installer and updater work
5. End-to-end release validation

Primary target:

- Convert runtime capabilities into a stable end-user product.

## Milestone Model

The project should advance through the following milestone sequence.

## M0: Architecture and Product Freeze

Purpose:

- Freeze execution posture before deeper implementation broadens the surface area.

Required deliverables:

1. Execution blueprint approved
2. Hermes integration mapping approved
3. Copilot runtime design approved
4. Skills/rules runtime design approved
5. Release gate model approved

Acceptance criteria:

1. There is no unresolved ambiguity about what is bridged, rebuilt, or deferred.
2. Each major subsystem has an owning layer and a defined contract boundary.
3. Release terminology is aligned with current product status.

## M1: Runtime Alpha

Purpose:

- Establish a real sidecar runtime with core product identity, not only engineering-preview infrastructure.

Required deliverables:

1. Real GitHub Copilot runtime path in `llm_gateway`
2. Hermes-derived session and memory integration first release
3. MetaFramework runtime integration first release
4. Strengthened health, error, and logging semantics
5. Persistence assumptions documented and enforced

Acceptance criteria:

1. A local sidecar session can execute against Copilot through normalized `llm_gateway` contracts.
2. Session and memory state survive restart according to documented MVP persistence rules.
3. Formal analysis remains callable in the loop without breaking module boundaries.
4. Runtime failures emit structured, diagnosable payloads.

## M2: Agent Alpha

Purpose:

- Turn the runtime into a strong local Agent rather than a minimal tool loop.

Required deliverables:

1. Explicit skill activation and rules loading
2. Web search runtime path
3. Stronger memory recall and session search
4. Broader MRAG ingest surface over sidecar contracts
5. Initial Agent-quality benchmark suite

Acceptance criteria:

1. A user can activate skills and rules for a session and see which were applied.
2. Agent tasks can use memory, tools, search, and formal analysis in one flow.
3. At least one benchmark suite exists for tool-use success, memory recall, and grounded response behavior.

## M3: Desktop Beta

Purpose:

- Deliver the first end-user-facing desktop shell with real workflows.

Required deliverables:

1. Electron shell with sidecar lifecycle supervision
2. Conversation UI
3. Knowledge-base UI
4. Analysis task UI
5. Settings and diagnostics UI
6. Artifact browser and export UI

Acceptance criteria:

1. A user can install and launch a desktop build locally.
2. The desktop can start, monitor, and restart the sidecar.
3. The desktop can manage knowledge bases, run analysis, and export artifacts.

## M4: Release Candidate

Purpose:

- Satisfy releasability rather than demonstration quality.

Required deliverables:

1. Installer and upgrade flow
2. Persistence migration handling
3. Sidecar crash recovery policy
4. Long-run stability validation
5. Performance baselines
6. Release notes, support boundaries, and operational diagnostics

Acceptance criteria:

1. Upgrade does not corrupt configuration, sessions, models, or knowledge bases.
2. Soak and restart tests complete without unresolved P0 or P1 failures.
3. Release packaging matches the documented Windows storage model.

## Release Gates

No milestone should be declared releasable without passing the corresponding gates.

### Gate 1: Product Integrity

Required:

1. README and release labels match actual readiness
2. No unsupported production claims remain in docs or packaging
3. The support boundary is explicit

### Gate 2: Storage and Upgrade Safety

Required:

1. No mutable runtime state is written into the install directory
2. Configuration, logs, cache, indexes, models, sessions, and artifacts follow the documented directory policy
3. Persistence format changes have migration or rebuild strategy
4. Restart and upgrade behavior is validated

### Gate 3: Runtime Safety and Diagnostics

Required:

1. Standardized health semantics across sidecar responses and desktop lifecycle states
2. Structured logs for start, stop, failure, degraded state, and recovery
3. Sidecar errors have stable top-level shape
4. Crash and timeout paths are diagnosable

### Gate 4: Extensibility Safety

Required:

1. Skills, rules, provider adapters, and artifacts have explicit lifecycle and version assumptions
2. Extension sources are attributable
3. Permission or trust boundaries are defined for user-loadable assets
4. Runtime injection does not rely on hidden or implicit behavior

### Gate 5: Agent Capability

Required:

1. Tool-call success behavior is benchmarked
2. Session resume quality is benchmarked
3. Memory recall and grounding quality are benchmarked
4. Formal analysis invocation and degraded handling are benchmarked
5. The product can explain when evidence is insufficient

### Gate 6: Desktop Release Readiness

Required:

1. Installer, upgrade, and uninstall validation
2. Desktop-sidecar end-to-end tests
3. Soak and restart coverage
4. Resource usage baselines for standard workflows

## Module-Level Direction

### `hermes_engine`

Must own:

1. Agent loop
2. Session state
3. Memory integration
4. Tool dispatch
5. Recovery policy

Must not own:

1. Provider-specific auth
2. Renderer state
3. Methodology grading policy

### `meta_harness`

Must own:

1. Formal analysis routing
2. Logic review
3. Reasonableness review
4. Evidence grade output
5. Degraded-state semantics for formal analysis results

Must not own:

1. Provider auth
2. General orchestration state
3. Desktop UI logic

### `llm_gateway`

Must own:

1. Provider/model/runtime execution
2. Copilot integration
3. Auth and credential handling
4. Provider gating
5. Skills/rules compatibility loading for normalized runtime use

Must not leak:

1. Provider-native SDK objects
2. External process handles beyond normalized runtime abstractions
3. Provider-specific response envelopes to upper layers

### `mrag_core`

Must own:

1. Parsing
2. Ingestion
3. Chunking
4. Retrieval
5. Citation and evidence packaging

Must not own:

1. Session memory
2. Model asset caches
3. Renderer formatting assumptions

### `artifact_engine`

Must evolve from a helper into a product subsystem for:

1. Structured export
2. Presentation export
3. Artifact provenance
4. Output verification metadata

### `asset_manager`

Must evolve from a helper into a product subsystem for:

1. Model and runtime asset installation
2. Download staging and promotion
3. Compatibility verification
4. Upgrade-safe local asset lifecycle

## Quality and Maintenance Model

This blueprint is also the maintenance guide for long-duration development.

### Ongoing Maintenance Rules

1. Every new capability must identify its owning subsystem.
2. Every new persisted format must declare version compatibility behavior.
3. Every new extension point must declare lifecycle and trust assumptions.
4. Every new product-facing flow must define how degraded state is surfaced.
5. Every major milestone must update the corresponding architecture, design, feature, and deployment documents.

### Documentation Maintenance Requirements

The following documents must stay aligned with implementation:

1. `docs/architecture/PycHermesAgent_Architecture_v0.2.0.md`
2. `docs/architecture/Hermes_Mixed_Integration_Mapping_v0.2.0.md`
3. `docs/architecture/PycHermesAgent_Solution_Architecture_v0.2.0.md`
4. `docs/architecture/Phase1_Roadmap_v0.2.0.md`
5. `docs/design/PycHermesAgent_Detailed_Design_v0.2.0.md`
6. `docs/features/PycHermesAgent_Feature_Details_v0.2.0.md`
7. `docs/deployment/PycHermesAgent_Usage_Deployment_Guide_v0.2.0.md`
8. This blueprint

### Acceptance Review Cadence

At the end of each milestone, review must answer all of the following:

1. What became truly implemented?
2. What remains partial?
3. Which old statements are now outdated and must be corrected?
4. Which release gates are now satisfied?
5. Which risks remain open?

## Immediate Execution Priorities

The next concrete development cycle should prioritize the following:

1. Freeze the Hermes mixed-integration mapping
2. Implement the first real GitHub Copilot runtime path
3. Implement a normalized instruction loader for rules and explicit skill activation
4. Deepen Hermes-derived session and memory behavior in `hermes_engine`
5. Define the first desktop-shell contract surface for settings, health, analysis, and artifacts

## Non-Goals For The Current Repository State

The following should still be treated as non-goals until the earlier milestones are complete:

1. Claiming production release readiness
2. Supporting every upstream Hermes plugin or runtime behavior
3. Cloning the entire `opencode` runtime
4. Building a full marketplace before core extension lifecycle is stable
5. Expanding desktop UI scope before sidecar runtime contracts are strong

## Related Documents

- `docs/architecture/Hermes_Mixed_Integration_Mapping_v0.2.0.md`
- `docs/architecture/PycHermesAgent_Architecture_v0.2.0.md`
- `docs/architecture/PycHermesAgent_Solution_Architecture_v0.2.0.md`
- `docs/architecture/Phase1_Roadmap_v0.2.0.md`
- `docs/design/PycHermesAgent_Detailed_Design_v0.2.0.md`
- `docs/features/PycHermesAgent_Feature_Details_v0.2.0.md`
- `docs/deployment/PycHermesAgent_Usage_Deployment_Guide_v0.2.0.md`
