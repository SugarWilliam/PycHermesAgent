# Phase 3D1 - Dynamic Skill Authoring Plan v0.3.0

**Status:** Proposed execution plan
**Authority:** `docs/Project_Development_and_Release_Governance.md`
**Parent roadmap:** `docs/architecture/Phase3D_Skills_Rules_Runtime_Plan_v0.3.0.md`
**Goal:** Add a safe, auditable, user-visible capability for PycHermesAgent to generate reusable skills on explicit user request and to synthesize candidate personal skills from long-term usage patterns, without enabling hidden code execution.

---

## 1. Scope

Phase 3D1 turns skills from a static discovery surface into a writable extension surface.

In scope:

- Generate a valid `SKILL.md` from an explicit user request.
- Save generated skills into approved project-level or user-level skill directories.
- Validate generated skill metadata and body structure before activation.
- Support candidate personal-skill synthesis from long-term preferences and repeated usage patterns.
- Require explicit review/approval before habit-derived skills become active.
- Expose sidecar APIs and desktop UX for creation, review, activation, and audit.

Out of scope:

- Executing arbitrary scripts from generated skills.
- Hidden or silent mutation of user instructions.
- Auto-publishing generated skills to remotes or sharing them externally.
- Turning skills into executable plugins in this phase.

---

## 2. Current Baseline

Current completed baseline includes:

- Skill discovery from `.opencode/skills/*/SKILL.md` in `src/pyc_hermes_agent/llm_gateway/skills.py`
- Skill metadata parsing in `src/pyc_hermes_agent/llm_gateway/skill_metadata.py`
- Builtin in-memory skill registry in `src/pyc_hermes_agent/hermes_engine/skills/registry.py`
- Explicit skill-context injection in `src/pyc_hermes_agent/hermes_engine/skill_context.py`
- Skill activation/usage audit in `src/pyc_hermes_agent/hermes_engine/skills/audit.py`
- Persistent user preferences in `src/pyc_hermes_agent/hermes_engine/memory.py`
- Desktop skill listing/toggling via `desktop/src/components/skills/*` and `desktop/src/store/skillStore.js`

Current missing capability:

- The product cannot create a new `SKILL.md` from a user request.
- The product cannot derive a reusable skill from recurring preferences or repeated usage patterns.
- The product has no candidate-skill review model.
- The sidecar has no skill-authoring routes.

---

## 3. Product Requirements

Dynamic skill authoring must cover two distinct flows.

### 3.1 Explicit User-Requested Skill Authoring

Examples:

- "Create a skill that always rewrites my analysis into executive-summary format."
- "Generate a reusable skill for weekly project status reports in Chinese."
- "Make a skill that outputs risk tables first and recommendations second."

Required behavior:

- Agent interprets the request as a skill-authoring task.
- Product generates a valid `SKILL.md` draft.
- Draft is shown to the user before activation.
- User chooses save location and activation state.
- Saved skill becomes discoverable immediately.

### 3.2 Preference / Habit-Derived Skill Synthesis

Examples:

- User repeatedly asks for bilingual output, structured tables, and risk-first summaries.
- User frequently requests the same report shape over many sessions.
- User consistently uses the same domain hints and output conventions.

Required behavior:

- Product detects stable recurring patterns from preferences and long-term usage summaries.
- Product generates a candidate personal skill proposal.
- Proposal includes reason, evidence, and suggested instructions.
- Proposal is never auto-activated silently.
- User can accept, edit, reject, or ignore the proposed skill.

---

## 4. Architecture Rules

- Generated skills must remain plain-text `SKILL.md` files inside supported skill directories.
- Runtime behavior continues to rely on explicit activation.
- Generated skills must not enable script execution.
- Skill generation and synthesis must be auditable.
- User-provided explicit instructions override inferred habit-derived skills.
- Habit-derived skills are proposals first, active runtime inputs only after explicit approval.
- `llm_gateway` remains the compatibility boundary for skill-file discovery/parsing.
- Desktop manages UX only; file-writing and validation behavior should live in Python-side services.

---

## 5. Data Model Additions

The implementation should introduce three new conceptual objects.

### 5.1 Authored Skill Draft

Purpose:

- Represents a newly generated skill before it is saved.

Suggested fields:

- `draft_id`
- `name`
- `description`
- `category`
- `body`
- `frontmatter`
- `source_kind` (`user_request` or `habit_synthesis`)
- `generation_reason`
- `created_at`

### 5.2 Personal Skill Proposal

Purpose:

- Represents a habit-derived skill candidate backed by observed usage patterns.

Suggested fields:

- `proposal_id`
- `candidate_name`
- `reason_summary`
- `supporting_signals`
- `recommended_body`
- `status` (`proposed`, `accepted`, `rejected`, `dismissed`)
- `created_at`

### 5.3 Skill Authoring Audit Entry

Purpose:

- Records draft creation, approval, rejection, save target, and activation decisions.

Suggested fields:

- `skill_id_or_draft_id`
- `action`
- `source_kind`
- `session_id`
- `timestamp`
- `details`

---

## 6. Target File Areas

### Core skill authoring

- new `src/pyc_hermes_agent/hermes_engine/skills/authoring.py`
- new `src/pyc_hermes_agent/hermes_engine/skills/validation.py`
- new `src/pyc_hermes_agent/hermes_engine/skills/storage.py`

### Habit synthesis and long-term personalization

- new `src/pyc_hermes_agent/hermes_engine/skills/personalization.py`
- `src/pyc_hermes_agent/hermes_engine/memory.py`
- `src/pyc_hermes_agent/hermes_engine/skills/audit.py`

### Discovery / compatibility integration

- `src/pyc_hermes_agent/llm_gateway/skills.py`
- `src/pyc_hermes_agent/llm_gateway/skill_metadata.py`

### Sidecar surfaces

- `src/pyc_hermes_agent/sidecar_api/services/skill_service.py`
- `src/pyc_hermes_agent/sidecar_api/http_server.py`
- `src/pyc_hermes_agent/sidecar_api/service.py`

### Desktop UX

- `desktop/src/components/skills/SkillPanel.jsx`
- `desktop/src/components/skills/SkillCard.jsx`
- new `desktop/src/components/skills/SkillAuthoringPanel.jsx`
- new `desktop/src/components/skills/SkillProposalPanel.jsx`
- `desktop/src/store/skillStore.js`
- `desktop/src/services/sidecarClient.js`

### Contracts and tests

- `src/pyc_hermes_agent/contracts/schemas.py`
- new `tests/contract/test_skill_authoring.py`
- new `tests/contract/test_skill_personalization.py`
- updates to `tests/contract/test_skills_system.py`
- updates to `tests/contract/test_skills_audit.py`

---

## 7. Workstreams

### D1. Skill Draft Generation

**Goal:** generate a valid skill draft from an explicit user request.

Required outcomes:

- Product can transform a user request into a structured `SKILL.md` draft.
- Frontmatter includes required fields such as `name` and `description`.
- Category is normalized to product-supported skill classes.
- Draft generation returns editable text, not only structured JSON.

Acceptance:

- User can request a reusable skill and receive a draft that passes metadata validation.

### D2. Skill Validation and Save Path

**Goal:** ensure generated skills are syntactically valid and stored safely.

Required outcomes:

- Validate frontmatter presence and required fields.
- Reject illegal or duplicate filenames according to policy.
- Save to approved project-level or user-level skill directories only.
- Preserve plain-text editability.

Acceptance:

- Saved skill becomes discoverable through the existing discovery path without manual restart.

### D3. Authoring Sidecar APIs

**Goal:** expose authoring and proposal workflows through stable local APIs.

Suggested route set:

- `POST /skills/drafts` create a draft from explicit request
- `POST /skills/drafts/{id}/save` save the draft into a skill directory
- `POST /skills/drafts/{id}/activate` activate after save
- `GET /skills/proposals` list habit-derived proposals
- `POST /skills/proposals/{id}/accept`
- `POST /skills/proposals/{id}/reject`

Required outcomes:

- Desktop can drive the entire workflow without writing files directly.
- API responses include provenance and validation messages.

Acceptance:

- All authoring flows can be performed via sidecar routes.

### D4. Habit Signal Collection

**Goal:** derive reusable skill candidates from stable behavior rather than one-off prompts.

Signal candidates:

- repeated `preferred_output_style`
- repeated `custom_instructions`
- recurring `domain_hints`
- repeated slash-command usage or repeated skill combinations
- repeated output-shape requests from multiple sessions

Required outcomes:

- Behavior is summarized over time instead of reacting to a single message.
- Signals are stored or derived in a way that is auditable.
- Explicit user preferences remain the strongest signal.

Acceptance:

- Product can produce a reasoned skill proposal from repeated usage patterns.

### D5. Candidate Personal Skill Synthesis

**Goal:** convert recurring habits into reviewable skill proposals.

Required outcomes:

- Product can generate a proposed skill body and name from detected patterns.
- Proposal includes why it was suggested.
- Proposal remains inactive until the user approves it.

Acceptance:

- User can review and accept a personal skill proposal generated from usage history.

### D6. Desktop Authoring and Review UX

**Goal:** make dynamic skill authoring a visible product capability.

Required outcomes:

- Desktop supports creating a skill from a prompt/request.
- Desktop supports reviewing, editing, saving, activating, rejecting, and dismissing proposals.
- Desktop clearly distinguishes:
  - builtin skills
  - user-authored skills
  - habit-derived proposals

Acceptance:

- User can manage the full authoring workflow from the desktop UI.

### D7. Audit, Safety, and Governance

**Goal:** ensure generated skills remain traceable and safe.

Required outcomes:

- Audit log records generation, save, approve, reject, and activation actions.
- No hidden auto-activation of synthesized skills.
- Skill generation keeps script execution disabled.
- Documentation and compatibility matrix reflect the new runtime semantics.

Acceptance:

- Dynamic skill authoring remains transparent, auditable, and policy-compliant.

---

## 8. Suggested UX Flow

### 8.1 Explicit authoring flow

1. User asks: "Create a skill for X"
2. Sidecar creates a draft
3. Desktop shows:
   - skill name
   - description
   - generated body
   - save target
4. User edits if needed
5. User saves
6. Product activates optionally
7. Audit trail records the event

### 8.2 Habit-derived proposal flow

1. Product detects stable usage pattern
2. Product creates candidate proposal
3. Desktop shows:
   - why it was proposed
   - example recurring signals
   - suggested `SKILL.md`
4. User chooses accept / edit / reject / dismiss
5. If accepted, product saves it as a normal skill
6. Audit trail records the event

---

## 9. Validation Rules

Generated skill validation should include:

- frontmatter exists
- required fields exist
- body is non-empty
- path is under approved skill root
- filename is sanitized
- generated content does not imply unsupported script execution
- category is one of allowed runtime categories

---

## 10. Execution Order

Recommended order:

1. D1 - Skill Draft Generation
2. D2 - Skill Validation and Save Path
3. D3 - Authoring Sidecar APIs
4. D4 - Habit Signal Collection
5. D5 - Candidate Personal Skill Synthesis
6. D6 - Desktop Authoring and Review UX
7. D7 - Audit, Safety, and Governance

Rationale:

- Explicit user-requested authoring is simpler and should land first.
- Habit-derived synthesis should build on the same draft/save/audit infrastructure.

---

## 11. Test Plan

Required verification:

- explicit skill-draft generation tests
- metadata validation tests
- save-path and path-policy tests
- sidecar authoring route tests
- proposal-generation tests from repeated preference/use patterns
- audit log tests
- desktop workflow tests where practical

Target test areas:

- new `tests/contract/test_skill_authoring.py`
- new `tests/contract/test_skill_personalization.py`
- `tests/contract/test_skills_system.py`
- `tests/contract/test_skills_audit.py`
- `tests/contract/test_sidecar_api.py`
- `tests/contract/test_sidecar_http.py`

---

## 12. Risks and Controls

| Risk | Impact | Control |
|------|--------|---------|
| Generated skill quality is poor | Bad runtime behavior | Validation, review UX, editable drafts |
| Habit-derived skills misrepresent user intent | Trust erosion | Proposal-only model, explicit user approval |
| Skill generation becomes hidden personalization | Loss of user control | No silent activation, full audit trail |
| Generated content suggests unsupported execution features | Policy drift | Validation rejects script-like execution semantics |
| Multiple skill sources become confusing | UX complexity | Source-kind labeling in sidecar and desktop |

---

## 13. Exit Definition

Phase 3D1 is complete when:

- User can explicitly request creation of a reusable skill and save it as a valid `SKILL.md`.
- Product can generate reviewable personal-skill proposals from repeated long-term usage patterns.
- All generated skills remain auditable, editable, and explicit-activation only.
- No dynamic skill path introduces hidden code execution or silent behavior mutation.

---
