# ADR: Skill Runtime Permissions — Phase 1 Scope and Deferrals (v0.2.0)

**Status:** Accepted  
**Governance:** `docs/Project_Development_and_Release_Governance.md`, `docs/architecture/Phase1_Roadmap_v0.2.0.md`

## Context

Skills are discovered via OpenCode/Cursor-compatible layouts (`.cursor/skills/`, `.opencode/skills/`). The product must not execute arbitrary skill scripts without an explicit permission and audit model. Phase 1 already ships **explicit activation** (`activated_skills` on `AgentLoopRequest`), **SKILL.md context injection**, and **script execution disabled** by policy.

## Decision

1. **Phase 1 (engineering preview) — in scope**  
   - Discovery and metadata listing (sidecar/hermes surfaces).  
   - **Explicit-only activation**: skills apply only when the caller lists them; no implicit “auto-run”.  
   - **Context binding**: SKILL.md text may be injected into the prompt path when activation is requested.  
   - **No script execution**: no subprocess/sandbox execution of skill entrypoints in this phase.

2. **Deferred to Phase 2+ (requires separate ADR)**  
   - **Permission model**: principals (user vs agent vs tool), allowlists, per-skill capabilities, revocation.  
   - **Script execution**: optional `SKILL.md` front-matter hooks, argv/env sandbox, timeouts, resource caps.  
   - **Audit trail**: durable logs of activation, denylists, and policy version.

3. **Explicit deferral statement**  
   Full “Discover → Parse → Activate → **Execute** → Audit” is **not** a Phase 1 exit requirement. Phase 1 exit for skills is satisfied when **explicit activation + metadata + no unsafe execution** are contract-tested and documented—which is the current line.

## Consequences

- External reports that claim “skill lifecycle incomplete” should be read as: **execution and permissions are intentionally deferred**, not accidental omissions.  
- Any feature that runs shell/code from a skill package **must not** ship without a new ADR and gates.  
- Desktop or sidecar UIs that list skills must present them as **advisory/metadata** unless execution ADR is in place.

## Follow-ups

- When prioritizing Phase 2: draft `ADR_Skill_Script_Execution_v0.x.md` referencing Windows packaging and `AGENTS.md` boundaries.  
- Link this ADR from `docs/constraints/opencode-compatibility.md` if skill semantics are described there.
