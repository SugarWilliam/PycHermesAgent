# opencode Compatibility Boundaries

| Field | Value |
| --- | --- |
| Date | 2026-05-14 |
| Version | v0.2.0 |
| Author | 彭耀成 |

## Supported Compatibility Targets

- `opencode.json`
- `opencode.jsonc`
- `AGENTS.md`
- `.opencode/skills/*/SKILL.md`

## Design Intent

Compatibility exists to reduce user learning cost. It is not a requirement to embed or duplicate the full `opencode` runtime.

## Implementation Rules

- Preserve `provider/model` identifiers.
- Preserve free-first model presentation.
- Preserve project rule and skill discovery semantics where practical.
- Keep compatibility logic inside `llm_gateway`.
