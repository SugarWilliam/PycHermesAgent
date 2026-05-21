"""Entry point for ``python -m pyc_hermes_agent`` and PyInstaller one-file bundles."""

from __future__ import annotations

from pyc_hermes_agent.sidecar_api.http_server import main

if __name__ == "__main__":
    raise SystemExit(main())
