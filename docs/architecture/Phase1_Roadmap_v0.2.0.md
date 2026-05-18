# PycHermesAgent Phase 1 Roadmap v0.2.0

**Status:** Active roadmap for engineering preview hardening
**Governance:** `docs/Project_Development_and_Release_Governance.md`

## 1. Phase 1 Goal

Phase 1 converts the current working MVP into a hardened local-first engineering preview with stable sidecar contracts, protected local persistence, explicit skill lifecycle, and measurable MetaHarness value. Phase 1 does not claim production readiness or desktop completeness.

## 2. Current Completed Baseline

Completed and contract-tested surfaces include:

- Sidecar health, config, provider/model/rule/skill discovery.
- HTTP JSON and SSE transport.
- Direct LLM runtime paths for configured OpenAI-compatible, OpenRouter, and GitHub Copilot style providers.
- Product-owned `AgentLoop` with tool calls, session persistence, bounded memory injection, planning, retry budgeting, and event streaming.
- `formal_analysis` tool integration through `MetaFramework.execute()`.
- Text MRAG knowledge bases with lexical retrieval and JSON persistence.
- Local asset and artifact foundations.

## 3. Remaining Phase 1 Workstreams

| Workstream | Required Result | Exit Gate |
|------------|-----------------|-----------|
| A: MRAG ownership | JSON storage guarded by owner/lock semantics | lock tests and restart tests pass |
| B: Trace propagation | request ID and trace ID visible across service, logs, events, and errors | HTTP and SSE contract tests pass |
| C: Skill lifecycle | explicit skill activation and context binding | no implicit execution; metadata visible |
| D: MetaHarness value | dependency-aware capability status and benchmark foundation | benchmark smoke passes |
| E: MRAG productization | file/url ingestion and index version behavior | retrieval and migration tests pass |
| F: Release gates | documented checklist + `scripts/release_gates.py` | script passes locally |

## 4. Workstream A: MRAG Ownership

Implementation must protect `mrag_core` persistence from uncoordinated multi-process writes. The accepted MVP is a single-process owner or lock guardrail. It is not necessary to implement a production database before this guardrail exists.

## 5. Workstream B: Trace Propagation

Every externally visible sidecar operation must become diagnosable. Request IDs must appear in errors, logs, and streaming events. Agent loop trace IDs remain separate and must be correlated rather than replaced.

## 6. Workstream C: Skill Lifecycle

Skill behavior must evolve in this order:

1. Discovery and metadata parsing.
2. Explicit activation request.
3. Controlled context binding.
4. Auditable activation metadata.
5. Permission-gated script execution in a later phase.

No skill script execution is allowed in Phase 1 without an explicit permission model.

## 7. Workstream D: MetaHarness Value

The evaluation report identified the most important risk: the methodology layer can become hollow if routing and judging remain only templates. Phase 1 must begin proving value through:

- realistic capability availability checks,
- method precondition checks,
- benchmark cases,
- degraded-state correctness,
- evidence-grade correctness.

## 8. Workstream E: MRAG Productization

MRAG remains local-first and evidence-grounded. Phase 1 may expose file and URL text ingestion and index version checks. Semantic embedding, reranking, and multimodal parsing remain later work unless the storage guardrail and migration rules are complete.

## 9. Workstream F: Release Gates

A preview release candidate may be tagged only when:

- `./.venv/bin/python -m pytest tests/contract` passes,
- scope-specific tests pass,
- docs are updated,
- compatibility matrix is updated for format/API changes,
- no secrets or runtime assets are staged,
- release notes exist (start from `scripts/generate_preview_release_notes.py` or `scripts/release_gates.py --write-preview-release-notes`; see `docs/releases/README.md`).

## 10. Phase 1 Exit Criteria

Phase 1 exits when:

1. Sidecar local transport has stable health, error, trace, and streaming semantics.
2. MRAG persistence is protected and restart-tested.
3. Skill lifecycle supports explicit activation without unsafe execution.
4. MetaHarness has dependency-aware routing and benchmark smoke coverage.
5. Release gates can produce a preview tag without manual reconstruction of the process (`scripts/release_gates.py` is the automated subset; human review remains required for secrets and policy).

The repository must still state clearly whether it is engineering preview, release candidate, or production release.
