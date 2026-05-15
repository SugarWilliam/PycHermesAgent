# PycHermesAgent Compatibility Matrix

| Field | Value |
| --- | --- |
| Date | 2026-05-14 |
| Version | v0.2.0 |
| Author | 彭耀成 |

## Version Axes

| Axis | Description |
| --- | --- |
| `app_version` | Desktop application release |
| `sidecar_api_version` | Renderer-to-sidecar API contract |
| `contract_version` | Schema version for runtime envelopes |
| `model_manifest_version` | Model asset manifest schema |
| `index_format_version` | Knowledge index format |
| `artifact_format_version` | Exported artifact format |

## Compatibility Rules

| Rule | Policy |
| --- | --- |
| App vs Sidecar API | Major version must remain compatible |
| Contract payloads | Reject incompatible major versions |
| Model assets | Must match manifest checksum and supported app range |
| Indexes | Rebuild on incompatible format changes |
| Artifacts | Allow independent evolution from core execution |

## `opencode` Scope

| Artifact | Support Level |
| --- | --- |
| `opencode.json` | Supported |
| `opencode.jsonc` | Supported |
| `AGENTS.md` | Supported |
| `.opencode/skills/*/SKILL.md` | Supported |
| Full plugin runtime | Not in Phase 0 |
| Hosted config sync | Not in Phase 0 |
