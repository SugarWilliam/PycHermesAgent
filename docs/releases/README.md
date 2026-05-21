# Preview release notes (drafts)

Engineering-preview tags should have human-edited release notes per
`docs/Project_Development_and_Release_Governance.md` and
`docs/Documentation_Tracking.md`.

Current-document-role note:

- `docs/releases/*.md` are release communication artifacts, not the authoritative source of current repository truth
- current contract/baseline truth lives in `docs/architecture/Compatibility_Matrix.md` and `docs/deployment/Production_Release_Gates.md`

**Generate a stub** (metadata + recent `git log`):

```bash
./.venv/bin/python scripts/generate_preview_release_notes.py -o docs/releases/preview_draft.md
```

**After full local gates** (contract tests, whitespace, secret scan):

```bash
./.venv/bin/python scripts/release_gates.py --write-preview-release-notes docs/releases/preview_draft.md
```

Commit the polished Markdown when cutting a preview tag; do not treat the auto stub as final copy.
