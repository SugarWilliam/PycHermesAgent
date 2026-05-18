"""Process-wide logging configuration for sidecar and CLI entrypoints."""

from __future__ import annotations

import logging
import os
import sys

_configured = False


def configure_sidecar_logging() -> None:
    """Configure root logging once. Use ``PYC_HERMES_LOG_FORMAT=json`` for newline-delimited JSON bodies only."""
    global _configured
    if _configured:
        return
    _configured = True
    level_name = os.environ.get("PYC_HERMES_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    fmt = os.environ.get("PYC_HERMES_LOG_FORMAT", "text").lower()
    if fmt == "json":
        logging.basicConfig(level=level, format="%(message)s", stream=sys.stdout, force=True)
    else:
        logging.basicConfig(
            level=level,
            format="%(levelname)s %(name)s %(message)s",
            stream=sys.stdout,
            force=True,
        )


__all__ = ["configure_sidecar_logging"]
