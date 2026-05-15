---
name: opencode-compat-audit
description: Audit project compatibility with opencode config, rules, and skills conventions
license: Proprietary
compatibility: opencode
metadata:
  audience: maintainers
  workflow: compatibility
---

## What I do
- Check `opencode.json` or `opencode.jsonc` discovery behavior
- Check `AGENTS.md` loading behavior
- Check `.opencode/skills/*/SKILL.md` discovery behavior
- Check that compatibility stays inside `llm_gateway`

## When to use me
Use this when changing config loading, rule discovery, or skill discovery.
