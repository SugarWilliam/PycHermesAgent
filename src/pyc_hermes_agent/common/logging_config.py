"""Process-wide logging configuration for sidecar HTTP and related services."""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from pathlib import Path

_configured_stderr = False
_file_handler_installed = False
_attached_file_logs_dir: Path | None = None

_SIDECAR_LOG = logging.getLogger("pyc_hermes_agent.sidecar_api")


def _detach_rotating_file_handlers() -> None:
    for handler in list(_SIDECAR_LOG.handlers):
        if isinstance(handler, logging.handlers.RotatingFileHandler):
            _SIDECAR_LOG.removeHandler(handler)
            try:
                handler.flush()
                handler.close()
            except OSError:
                pass


def configure_sidecar_logging(*, logs_dir: Path | None = None) -> None:
    """Attach stderr formatting once. Optional rotating file sink when *logs_dir* is set."""
    global _configured_stderr
    if _configured_stderr:
        maybe_attach_file_logging(logs_dir=logs_dir)
        return
    _configured_stderr = True

    level_name = os.environ.get("PYC_HERMES_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    fmt = os.environ.get("PYC_HERMES_LOG_FORMAT", "text").lower()
    if fmt == "json":
        formatter: logging.Formatter = logging.Formatter("%(message)s")
    else:
        formatter = logging.Formatter("%(levelname)s %(name)s %(message)s")

    _SIDECAR_LOG.setLevel(level)
    _SIDECAR_LOG.handlers.clear()

    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(formatter)
    _SIDECAR_LOG.addHandler(stream)
    _SIDECAR_LOG.propagate = False

    maybe_attach_file_logging(logs_dir=logs_dir)


def maybe_attach_file_logging(*, logs_dir: Path | None = None) -> None:
    """Rotating NDJSON-compatible file alongside stdout events (same %(message)s body)."""
    global _file_handler_installed, _attached_file_logs_dir
    disable = os.environ.get("PYC_HERMES_DISABLE_FILE_LOG", "").lower() in ("1", "true", "yes")
    if disable:
        _detach_rotating_file_handlers()
        _file_handler_installed = False
        _attached_file_logs_dir = None
        return

    if logs_dir is None:
        _detach_rotating_file_handlers()
        _file_handler_installed = False
        _attached_file_logs_dir = None
        return

    resolved = logs_dir.resolve()
    if _file_handler_installed and _attached_file_logs_dir == resolved:
        return

    _detach_rotating_file_handlers()
    _file_handler_installed = False
    _attached_file_logs_dir = None

    logs_dir.mkdir(parents=True, exist_ok=True)

    path = resolved / "sidecar-events.log"
    max_bytes = int(os.environ.get("PYC_HERMES_LOG_FILE_MAX_BYTES", "10485760"))
    backups = int(os.environ.get("PYC_HERMES_LOG_FILE_BACKUPS", "5"))

    fh = logging.handlers.RotatingFileHandler(
        path,
        maxBytes=max_bytes,
        backupCount=backups,
        encoding="utf-8",
    )
    fh.setFormatter(logging.Formatter("%(message)s"))
    level_name = os.environ.get("PYC_HERMES_LOG_LEVEL", "INFO").upper()
    fh.setLevel(getattr(logging, level_name, logging.INFO))
    _SIDECAR_LOG.addHandler(fh)
    _file_handler_installed = True
    _attached_file_logs_dir = resolved


__all__ = ["configure_sidecar_logging", "maybe_attach_file_logging"]
