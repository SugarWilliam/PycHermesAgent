# Phase 3D - Skills and Rules Runtime Plan v0.3.0

**Status:** Proposed execution plan
**Authority:** `docs/Project_Development_and_Release_Governance.md`
**Parent roadmap:** `docs/architecture/Phase3_Phase4_Productization_Roadmap_v0.3.0.md`
**Goal:** Upgrade the current skill and rule system from metadata discovery plus builtin activation into a customer-loadable, auditable, runtime-effective extension system, including agent-authored skills from explicit user requests and long-term usage patterns, without violating existing safety boundaries.

---

## 1. Scope

Phase 3D focuses on extension surfaces that affect agent behavior:

- project and user skill discovery
- runtime activation and prompt assembly
- rule discovery and precedence
- builtin versus user extension separation
- user-requested skill generation
- preference / habit / long-term usage driven skill synthesis
- auditability and desktop management

In scope:

- `.opencode/skills` compatibility improvements
- user-level skill directories
- runtime rule composition
- extension provenance and audit
- skill authoring from explicit user requests
- skill proposal / generation from repeated usage patterns and preferences
- desktop UX for skills and rule visibility

Out of scope:

- arbitrary script execution
- unreviewed plugin execution model
- provider-native extension hooks bypassing `llm_gateway`
- turning skills into code plugins in this phase

---

## 2. Current Baseline

Current completed baseline includes:

- `llm_gateway/skills.py` discovers `.opencode/skills/*/SKILL.md`
- `llm_gateway/rules.py` discovers `AGENTS.md` or `CLAUDE.md`
- `hermes_engine/skill_context.py` supports explicit skill-context injection
- `hermes_engine/skills/registry.py` manages builtin in-memory skills
- `hermes_engine/skills/audit.py` records skill activation and usage
- `hermes_engine/memory.py` persists user preferences only
- desktop already lists builtin skills and can toggle them

Current gap:

- User-provided skills are discoverable but not first-class runtime-managed objects.
- Rules are discoverable but not assembled into a deterministic runtime policy chain.
- There is no full provenance model spanning builtin, project, and user-loaded sources.
- The agent cannot currently generate new `SKILL.md` files on user request.
- The agent does not currently learn repeated habits/preferences and promote them into synthesized skills.

---

## 3. Architecture Rules

- Skill activation remains explicit.
- Generated skills must remain editable plain files under supported skill directories.
- Habit-derived skill generation must remain reviewable and auditable; no silent hidden mutation of user behavior instructions.
- Skill script execution remains disabled until a later permissions model is approved.
- Rule assembly must be deterministic and inspectable.
- Skills and rules influence prompt/context construction, not provider internals.
- Provider/model/auth logic stays confined to `llm_gateway`.
- Extension provenance and audit must remain available through sidecar surfaces.

---

## 4. Workstreams

### D1. User Skill Discovery Paths

**Goal:** extend discovery beyond project-local `.opencode/skills` while preserving compatibility.

Target files:

- `src/pyc_hermes_agent/llm_gateway/skills.py`
- `src/pyc_hermes_agent/llm_gateway/skill_metadata.py`
- `src/pyc_hermes_agent/common/runtime_paths.py`
- `src/pyc_hermes_agent/sidecar_api/services/skill_service.py`

Required outcomes:

- Project-level and user-level skill directories are both supported.
- Skill metadata includes source provenance.
- Conflicts are resolved deterministically.

Acceptance:

- A user can add a skill without modifying product code.

### D2. Builtin vs User Skill Model

**Goal:** make skill source categories explicit in runtime and UI.

Target files:

- `src/pyc_hermes_agent/hermes_engine/skills/registry.py`
- `src/pyc_hermes_agent/hermes_engine/skills/builtin_skills.py`
- `src/pyc_hermes_agent/sidecar_api/services/skill_service.py`
- `desktop/src/components/skills/SkillPanel.jsx`
- `desktop/src/components/skills/SkillCard.jsx`

Required outcomes:

- Skill definitions distinguish builtin, project, and user source kinds.
- Desktop can show provenance and trust level.
- Builtin skills remain pre-registered but not confused with discovered user skills.

Acceptance:

- Sidecar and desktop both expose where each skill came from.

### D3. Runtime Skill Assembly

**Goal:** ensure active skills materially influence the runtime in a deterministic way.

Target files:

- `src/pyc_hermes_agent/hermes_engine/skill_context.py`
- `src/pyc_hermes_agent/hermes_engine/agent_loop.py`
- `src/pyc_hermes_agent/sidecar_api/services/chat_service.py`

Required outcomes:

- Runtime skill assembly preserves explicit ordering rules.
- Unknown or invalid skills fail clearly.
- Skill source and activation metadata are carried through the run path.

Acceptance:

- Skill activation changes prompt/context behavior in a traceable manner.

### D4. Rule Precedence Model

**Goal:** convert rule discovery into a real runtime prompt-assembly policy.

Target files:

- `src/pyc_hermes_agent/llm_gateway/rules.py`
- new rule assembly helper under `src/pyc_hermes_agent/llm_gateway/`
- `src/pyc_hermes_agent/hermes_engine/agent_loop.py`
- `src/pyc_hermes_agent/sidecar_api/services/common.py`

Required outcomes:

- Rule precedence is documented and encoded in code.
- Product/system rules, project rules, user rules, and skill fragments no longer compete ambiguously.
- The runtime can surface which rules were active.

Acceptance:

- A run can show deterministic rule order and effective prompt inputs.

### D5. Audit and Provenance Expansion

**Goal:** record enough extension metadata to support debugging and review.

Target files:

- `src/pyc_hermes_agent/hermes_engine/skills/audit.py`
- `src/pyc_hermes_agent/sidecar_api/services/skill_service.py`
- `src/pyc_hermes_agent/sidecar_api/http_server.py`
- desktop stores/components under `desktop/src/store/*`

Required outcomes:

- Audit entries include activation, deactivation, source kind, and usage context.
- Sidecar surfaces can return recent extension activity.
- Desktop can inspect audit history.

Acceptance:

- Users can tell which extensions were active during a run.

### D6. User-Requested Skill Authoring

**Goal:** let the agent create reusable skills when the user explicitly asks for one.

Target files:

- `src/pyc_hermes_agent/llm_gateway/skill_metadata.py`
- `src/pyc_hermes_agent/llm_gateway/skills.py`
- new `src/pyc_hermes_agent/hermes_engine/skills/authoring.py`
- `src/pyc_hermes_agent/sidecar_api/services/skill_service.py`
- `src/pyc_hermes_agent/sidecar_api/http_server.py`
- `desktop/src/components/skills/*`

Required outcomes:

- Agent can generate a valid `SKILL.md` scaffold and content from explicit user intent.
- New skills can be saved into approved project-level or user-level skill directories.
- Skill creation is audited with source, timestamp, and generation reason.
- Generated skills are plain-text artifacts that the user can inspect and edit.

Acceptance:

- User can ask the product to create a reusable skill and then immediately activate or edit it.

### D7. Preference and Habit-Derived Skill Synthesis

**Goal:** let the product promote repeated long-term behavior into reusable skills, under explicit reviewable rules.

Target files:

- `src/pyc_hermes_agent/hermes_engine/memory.py`
- new `src/pyc_hermes_agent/hermes_engine/skills/personalization.py`
- `src/pyc_hermes_agent/hermes_engine/skills/audit.py`
- `src/pyc_hermes_agent/sidecar_api/services/skill_service.py`
- `desktop/src/components/skills/*`

Required outcomes:

- Repeated user preferences, prompt patterns, and stable output habits can be summarized into candidate skills.
- Candidate skills are reviewable before activation or persistence.
- The product distinguishes between inferred skill proposals and user-authored skills.
- Long-term usage signals do not silently overwrite explicit user instructions.

Acceptance:

- The agent can suggest or generate personal reusable skills from extended usage history and preferences.

### D8. Desktop Extension Management UX

**Goal:** let users manage extensions from the desktop, not only the filesystem.

Target files:

- `desktop/src/components/skills/*`
- `desktop/src/components/settings/SettingsPanel.jsx`
- `desktop/src/store/skillStore.js`
- `desktop/src/services/sidecarClient.js`

Required outcomes:

- Users can list, filter, activate, deactivate, and inspect skills.
- Rule sources can be inspected from the UI.
- Errors remain understandable when discovered skills are invalid.

Acceptance:

- Desktop is a usable control surface for extension management.

### D9. Permissions Boundary Integrity

**Goal:** preserve safety while expanding extension power.

Target files:

- `src/pyc_hermes_agent/hermes_engine/skill_context.py`
- `docs/constraints/opencode-compatibility.md`
- `docs/architecture/Compatibility_Matrix.md`

Required outcomes:

- Script execution remains explicitly disabled.
- Any future permissions plan is documented as deferred, not silently implied.

Acceptance:

- No extension feature in this phase introduces hidden code execution.

---

## 5. Execution Order

Recommended order:

1. D1 - User Skill Discovery Paths
2. D2 - Builtin vs User Skill Model
3. D3 - Runtime Skill Assembly
4. D4 - Rule Precedence Model
5. D5 - Audit and Provenance Expansion
6. D6 - User-Requested Skill Authoring
7. D7 - Preference and Habit-Derived Skill Synthesis
8. D8 - Desktop Extension Management UX
9. D9 - Permissions Boundary Integrity

---

## 6. Test Plan

Required verification:

- skill discovery tests for project and user scopes
- rule precedence tests
- runtime assembly tests
- audit persistence tests
- generated skill validity tests
- habit-derived skill proposal tests
- desktop extension UI tests where available

Target test areas:

- `tests/contract/test_skills_system.py`
- `tests/contract/test_skills_audit.py`
- `tests/contract/test_opencode_compat.py`
- new `tests/contract/test_rules_runtime.py`
- new `tests/contract/test_skill_authoring.py`
- new `tests/contract/test_skill_personalization.py`
- `tests/contract/test_sidecar_api.py`
- `tests/contract/test_sidecar_http.py`

---

## 7. Risks

| Risk | Impact | Control |
|------|--------|---------|
| User skills shadow builtin behavior unexpectedly | Confusing runtime behavior | Explicit source kind and precedence rules |
| Rules become non-deterministic | Debugging difficulty | Deterministic assembly order and audit output |
| Habit-derived skills drift away from user intent | Personalization trust loss | Reviewable proposals and explicit approval before activation |
| Generated skills contain low-quality or contradictory instructions | Runtime quality regression | Skill validation, provenance, and editable plain-text output |
| Extension system drifts toward unsafe execution | Security risk | Keep script execution disabled |

---

## 8. Exit Definition

Phase 3D is complete when:

- User-loaded skills are first-class runtime-managed objects.
- The agent can generate reusable skills on explicit user request.
- The system can synthesize reviewable personal skills from repeated preferences and long-term usage patterns.
- Rules participate in deterministic runtime assembly.
- Audit and provenance are inspectable through sidecar and desktop surfaces.
- Safety boundaries remain intact.

---
