# Windows Packaging Boundaries

| Field | Value |
| --- | --- |
| Date | 2026-05-14 |
| Version | v0.2.0 |
| Author | 彭耀成 |

## Directory Rules

- Install directory is read-only.
- Configuration lives in `%APPDATA%`.
- Logs, cache, downloads, indexes, and models live in `%LOCALAPPDATA%`.
- Models must use `model-id/revision-or-sha` directory layout.
- Downloads must be promoted atomically after checksum validation.

## Upgrade Rules

- App updates and model updates are separate concerns.
- Sidecar runtime ships with the app.
- Model assets follow a manifest with checksum and compatibility range.

## Risk Guardrails

- No mutable runtime state in the install directory.
- No implicit feature availability based on silent import failures.
- No mixed responsibility between Electron and the sidecar for model downloads.
