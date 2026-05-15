---
name: windows-packaging-guard
description: Review Windows install, runtime, model, and cache boundaries for packaging safety
license: Proprietary
compatibility: opencode
metadata:
  audience: maintainers
  workflow: packaging
---

## What I do
- Check install directory immutability
- Check `%APPDATA%` and `%LOCALAPPDATA%` separation
- Check model asset promotion and checksum validation flow
- Check update boundaries between app runtime and model assets

## When to use me
Use this when changing path resolution, packaging, updates, or asset downloads.
