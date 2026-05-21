---
name: architecture-boundary-review
description: Review cross-module changes for boundary drift, coupling growth, and protocol safety
license: Proprietary
compatibility: opencode
metadata:
  audience: maintainers
  workflow: architecture
---

## What I do
- Check whether one layer depends on deeper implementation details
- Check whether a new change leaks contracts across boundaries
- Check whether a change adds untyped or implicit payloads

## When to use me
Use this when adding new runtime capabilities or changing module interfaces.
