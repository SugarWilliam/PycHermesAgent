# Asset Promotion Strategy v0.2.0

**Status:** Architecture decision record (ADR)  
**Governance:** `docs/Project_Development_and_Release_Governance.md` Phase 2

## Context

Model assets are installed under the runtime `models_dir` with manifest metadata. Writes must not corrupt an existing install or leave a half-written tree visible to readers.

## Strategy (implemented)

1. **Staging directory** — Payloads are assembled under `downloads_dir / "model-staging" / stage-{uuid}` (see `AssetManager._create_staging_dir`).
2. **Validate before promote** — Checksums, sizes, compatibility fields, and path segments are validated before any content is promoted (`_validate_install`).
3. **Atomic promotion** — On POSIX and Windows, `Path.replace(staging_dir, target_dir)` is used when the final path does not exist. This is atomic when source and target live on the same file system; runtime paths place both under the same local application-data root.
4. **Cleanup** — `finally` removes the staging directory after success or failure so orphans do not accumulate.
5. **Idempotent re-install** — If the target version already exists and matches the requested manifest and checksum, promotion is skipped.

## Failure modes

- Checksum or size mismatch: raises before staging is promoted; **no** entry under `models_dir` for a new install.
- Reserved filename or invalid segments: raises during validation or copy; target directory unchanged.
- `FileExistsError` on promote: indicates an unexpected race or on-disk collision; caller must not assume partial install.

## Non-goals (v0.2.x)

- Cross-volume copy-then-rename fallback (not required when staging and models share one data root).
- Concurrent multi-process installs to the same `(asset_id, version)` (single-writer assumption for preview).
