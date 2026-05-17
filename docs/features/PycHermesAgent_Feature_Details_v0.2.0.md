# PycHermesAgent Feature Details v0.2.0

**Status:** Feature state matrix for production-bound development

## 1. State Legend

| State | Meaning |
|-------|---------|
| Implemented | Contract-tested and usable in engineering preview |
| Partial | Present but limited or not production-hardened |
| Planned | Designed but not implemented |
| Production Gate | Required before production release |

## 2. Feature Matrix

| Feature | State | Current Evidence | Production Gate |
|---------|-------|------------------|-----------------|
| Sidecar Python API | Implemented | `sidecar_api.service` and contract tests | trace and versioning hardened |
| Sidecar HTTP JSON | Implemented | stdlib HTTP route tests | release smoke and error consistency |
| Sidecar SSE | Partial | LLM and AgentLoop streaming tests | request correlation and failure semantics |
| Hermes read-only bridge | Implemented | `HermesFacade` snapshots | keep diagnostic, not runtime owner |
| Product AgentLoop | Partial | tool calls, sessions, planning, retries | stronger trace and skill lifecycle |
| Session persistence | Implemented | JSON session store tests | migration and search policy later |
| Memory injection | Partial | bounded prompt injection | retrieval-backed memory policy later |
| MetaHarness entry point | Implemented | `MetaFramework.execute()` tests | benchmark value proof |
| Capability availability | Partial | descriptor-based today | dependency-aware bridge status |
| Method selection | Partial | heuristic route today | data-shape and precondition routing |
| LLM runtime | Partial | Copilot/OpenAI-compatible/OpenRouter paths | broader mock matrix and release config docs |
| Skill discovery | Implemented | metadata parsing tests | explicit activation and audit trail |
| Skill runtime binding | Planned | none | no implicit execution; context binding first |
| MRAG text ingest | Implemented | text service and tests | file/url HTTP surfaces |
| MRAG persistence | Partial | JSON persistence | lock/ownership and migration/rebuild behavior |
| MRAG retrieval | Partial | lexical search | citations, indexing strategy, rerank path |
| Asset manager | Partial | local validation/promotion tests | sidecar route and durability policy |
| Artifact engine | Partial | export/list tests | sidecar route and desktop integration |
| Electron shell | Planned | no product shell | after sidecar contracts stabilize |
| Release automation | Planned | governance now defined | gates, tag, release notes, push policy |

## 3. Adopted Evaluation Findings

The evaluation report identified five feature gaps that are now official roadmap inputs:

- MetaHarness must prove value with benchmarks.
- MRAG must move beyond lexical MVP in controlled phases.
- Skill lifecycle must move beyond discovery.
- Quality gates must include CI/smoke/release checks.
- Markdown/desktop rendering matters for product UX but follows runtime hardening.

## 4. Production Readiness Checklist

A feature can be marked production-ready only when:

- contracts are stable and tested,
- degraded/error states are documented,
- persistence and migration behavior are defined where applicable,
- runtime paths follow packaging rules,
- release notes can describe user impact and rollback risk,
- no architecture boundary is weakened.
