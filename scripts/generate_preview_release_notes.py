#!/usr/bin/env python3
"""Generate a Markdown draft for engineering-preview releases (human polish required).

Governance: ``docs/Project_Development_and_Release_Governance.md`` and
``docs/releases/README.md``.

Usage (from repo root):

    ./.venv/bin/python scripts/generate_preview_release_notes.py
    ./.venv/bin/python scripts/generate_preview_release_notes.py -o docs/releases/preview_draft.md
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _git(*args: str) -> str | None:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _draft_body() -> str:
    sys.path.insert(0, str(ROOT / "src"))
    from pyc_hermes_agent import __version__
    from pyc_hermes_agent.sidecar_api.service import SIDECAR_API_VERSION

    rev = _git("rev-parse", "--short", "HEAD") or "unknown"
    branch = _git("rev-parse", "--abbrev-ref", "HEAD") or "unknown"
    when = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    log_block = _git("log", "-n", "25", "--oneline") or "(git log unavailable)"
    lines = [
        "# PycHermesAgent — preview release notes (draft)\n",
        "\n",
        "> **Auto-generated stub.** Edit for users before tagging; see "
        "`docs/Project_Development_and_Release_Governance.md` gate policy.\n",
        "\n",
        "## Build metadata\n",
        "\n",
        f"- **Generated (UTC):** {when}\n",
        f"- **Git:** `{rev}` on `{branch}`\n",
        f"- **Package `__version__`:** `{__version__}`\n",
        f"- **`sidecar_api_version`:** `{SIDECAR_API_VERSION}`\n",
        "\n",
        "## Recent commits\n",
        "\n",
        "```text\n",
        log_block + "\n",
        "```\n",
        "\n",
        "## Suggested manual sections\n",
        "\n",
        "- Features / fixes (user-facing)\n",
        "- Migration (MRAG index, sidecar API, desktop)\n",
        "- Known limitations (engineering preview)\n",
        "- Verification: `scripts/release_gates.py` and scope tests\n",
    ]
    return "".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate preview release notes draft")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        metavar="FILE",
        help="Write Markdown to this file instead of stdout",
    )
    args = parser.parse_args(argv)
    body = _draft_body()
    if args.output is not None:
        out = args.output.resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(body, encoding="utf-8")
        print(f"+ wrote {out}", flush=True)
    else:
        print(body, end="", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
