# OpenCode Compatibility Constraints

**Status:** Hard constraint

## 1. Compatibility Scope

PycHermesAgent supports compatibility with:

- `opencode.json` and `opencode.jsonc`,
- `AGENTS.md`,
- `.opencode/skills/*/SKILL.md`,
- provider/model style identifiers.

The project must not clone the complete OpenCode runtime.

## 2. LLM Boundary

OpenCode-style provider and model compatibility belongs in `llm_gateway`. Provider-specific details must not leak into `hermes_engine`, `meta_harness`, `mrag_core`, or the desktop shell.

## 3. Skill Lifecycle

Skill compatibility evolves through explicit phases:

1. discover,
2. parse metadata,
3. explicit activation,
4. controlled context binding,
5. audited runtime behavior,
6. permission-gated script execution later.

Implicit execution of discovered skills is forbidden. Script execution requires a future permission model and audit trail.

## 4. Free-First Presentation

Default model presentation must remain free-first unless a user explicitly configures otherwise.

## 5. Release Gate

Any change to OpenCode compatibility requires:

- compatibility tests,
- sidecar list/config tests when exposed,
- documentation update,
- no provider-native object leakage.
