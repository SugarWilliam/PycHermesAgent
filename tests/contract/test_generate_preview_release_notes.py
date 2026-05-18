"""Contract smoke for preview release-notes generator."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_generate_preview_release_notes_script_writes_markdown(tmp_path) -> None:
    out = tmp_path / "preview_notes.md"
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "generate_preview_release_notes.py"), "-o", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    body = out.read_text(encoding="utf-8")
    assert "preview release notes" in body.lower()
    assert "sidecar_api_version" in body
    assert "__version__" in body
