"""Minimal structured logging helpers for the sidecar transport."""

from __future__ import annotations

import json
import logging
from typing import Any

_LOGGER = logging.getLogger("pyc_hermes_agent.sidecar_api")


def log_event(event: str, **fields: Any) -> None:
    """Emit one structured record (stderr and optional rotating log file configured at server start)."""
    if not _LOGGER.handlers:
        from pyc_hermes_agent.common.logging_config import configure_sidecar_logging

        configure_sidecar_logging()
    payload = {"event": event, **fields}
    _LOGGER.info(json.dumps(payload, ensure_ascii=True, sort_keys=True))


__all__ = ["log_event"]
