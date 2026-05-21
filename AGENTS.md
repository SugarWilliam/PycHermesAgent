# PycHermesAgent Project Rules

## Metadata
- Date: 2026-05-26
- Version: v0.3.0
- Author: 彭耀成
- Phase 1 (engineering preview): **roadmap complete** for declared scope — see `docs/architecture/Phase1_Roadmap_v0.2.0.md` §10 (not production).
- Phase 2 (usable workbench): **complete** — see `docs/architecture/Phase2_Toward_GA_v0.2.1.md` (not production).

## Project Identity
- Product name: `PycHermesAgent`
- Repo root: `PycHermersAgent/`
- Product direction: `Hermes Engine + MetaHarness + opencode-style LLM + local-first MRAG + Electron Desktop`

## Non-Negotiable Boundaries
- Formal analysis must go through `MetaFramework.execute()`.
- Do not merge `Hermes Engine` orchestration logic into `MetaHarness`.
- Do not let provider-specific SDK objects leak beyond `llm_gateway`.
- Do not let `mrag_core` become a mixed store for logs, model assets, and chat memory.
- Do not write mutable runtime assets into the install directory.
- Do not treat predictive outputs as intervention-grade causal claims.

## Runtime Boundaries
- `hermes_engine` owns orchestration, session state, memory, and tool loop.
- `meta_harness` owns method selection, logic review, reasonableness review, and evidence grading.
- `llm_gateway` owns provider/model/auth/config compatibility.
- `mrag_core` owns ingestion, indexing, retrieval, rerank, and evidence packaging.
- `sidecar_api` owns stable local API contracts for the desktop shell.

## Delivery Order
1. Governance documents, rules, and skills
2. Package skeleton and contracts
3. `MetaHarness` minimum viable base
4. `opencode` compatibility layer
5. Hermes integration seam
6. Local-first MRAG
7. Electron desktop shell

## Compatibility Scope
- Keep compatibility with `opencode.json/jsonc`, `AGENTS.md`, and `.opencode/skills/*/SKILL.md`.
- Do not attempt to clone the full `opencode` runtime.
- Prefer `provider/model` identifiers across the LLM layer.
- Default model presentation must remain free-first.

## Packaging Rules
- Install directory is read-only.
- Configuration lives in `%APPDATA%`.
- Logs, cache, indexes, downloads, and models live in `%LOCALAPPDATA%`.
- Model downloads must use a temporary directory, checksum validation, and atomic promotion.

## MetaHarness Rules
- `MetaHarness` is a harness, not a monolithic runtime.
- It must remain usable with different LLM backends.
- It must output method rationale, assumptions, evidence grade, risks, and degraded state.
- CE and SR grading must remain separated.

## Testing Priority
- Contract tests first
- Harness smoke tests second
- Compatibility tests third
- Integration tests fourth
- Desktop UI tests last
