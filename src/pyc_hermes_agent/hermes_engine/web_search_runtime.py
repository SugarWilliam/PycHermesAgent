"""Track B — TTL disk cache, per-process quota windows, backoff, latency meta for web_search."""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pyc_hermes_agent.common import ensure_runtime_directories, resolve_runtime_paths

_LOCK = threading.RLock()

_MINUTE_SLOT: int = -1
_MINUTE_USES: int = 0
_HOUR_SLOT: int = -1
_HOUR_USES: int = 0

_PROVIDER_FAILURES: dict[str, list[float]] = {}
_BACKOFF_UNTIL: dict[str, float] = {}


def resolve_web_search_cache_dir(workspace_root: Path | None) -> Path:
    root = workspace_root.resolve() if workspace_root is not None else Path.cwd().resolve()
    paths = ensure_runtime_directories(resolve_runtime_paths(root))
    return paths.cache_dir / "web_search"


def cache_ttl_seconds() -> int:
    raw = os.environ.get("PYC_HERMES_WEB_SEARCH_CACHE_TTL_SEC", "900").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 900


def quota_limits() -> tuple[int, int]:
    try:
        per_minute = max(1, int(os.environ.get("PYC_HERMES_WEB_SEARCH_QUOTA_PER_MINUTE", "120")))
    except ValueError:
        per_minute = 120
    try:
        per_hour = max(per_minute, int(os.environ.get("PYC_HERMES_WEB_SEARCH_QUOTA_PER_HOUR", "2400")))
    except ValueError:
        per_hour = 2400
    return per_minute, per_hour


def try_consume_network_quota_slot() -> tuple[bool, dict[str, Any]]:
    """Each successful reservation counts one outbound-resolution attempt."""

    global _MINUTE_SLOT, _MINUTE_USES, _HOUR_SLOT, _HOUR_USES

    now = time.time()
    minute_id = int(now // 60)
    hour_id = int(now // 3600)
    per_min, per_hour = quota_limits()

    with _LOCK:
        if _MINUTE_SLOT != minute_id:
            _MINUTE_SLOT = minute_id
            _MINUTE_USES = 0
        if _HOUR_SLOT != hour_id:
            _HOUR_SLOT = hour_id
            _HOUR_USES = 0

        if _MINUTE_USES >= per_min:
            remaining_min = max(0, per_min - _MINUTE_USES)
            remaining_hour = max(0, per_hour - _HOUR_USES)
            return False, {
                "quota_window": "minute",
                "quota_per_minute": per_min,
                "quota_per_hour": per_hour,
                "quota_remaining_minute_approx": remaining_min,
                "quota_remaining_hour_approx": remaining_hour,
            }

        if _HOUR_USES >= per_hour:
            return False, {
                "quota_window": "hour",
                "quota_per_minute": per_min,
                "quota_per_hour": per_hour,
                "quota_remaining_minute_approx": max(0, per_min - _MINUTE_USES),
                "quota_remaining_hour_approx": max(0, per_hour - _HOUR_USES),
            }

        _MINUTE_USES += 1
        _HOUR_USES += 1

        return True, {
            "quota_window": None,
            "quota_per_minute": per_min,
            "quota_per_hour": per_hour,
            "quota_remaining_minute_approx": max(0, per_min - _MINUTE_USES),
            "quota_remaining_hour_approx": max(0, per_hour - _HOUR_USES),
        }


def provider_backoff_until(provider_key: str) -> float | None:
    with _LOCK:
        until = float(_BACKOFF_UNTIL.get(provider_key, 0.0))
    if until <= time.time():
        return None
    return until


def note_provider_failure(provider_key: str) -> None:
    try:
        window_sec = float(os.environ.get("PYC_HERMES_WEB_SEARCH_FAILURE_WINDOW_SEC", "120"))
    except ValueError:
        window_sec = 120.0
    try:
        fail_threshold = max(2, int(os.environ.get("PYC_HERMES_WEB_SEARCH_BACKOFF_AFTER_FAILURES", "3")))
    except ValueError:
        fail_threshold = 3
    try:
        backoff_sec = float(os.environ.get("PYC_HERMES_WEB_SEARCH_BACKOFF_SEC", "45"))
    except ValueError:
        backoff_sec = 45.0

    now = time.time()
    with _LOCK:
        buf = _PROVIDER_FAILURES.setdefault(provider_key, [])
        buf.append(now)
        buf[:] = [t for t in buf if now - t <= window_sec]
        if len(buf) >= fail_threshold:
            _BACKOFF_UNTIL[provider_key] = now + backoff_sec


def note_provider_success(provider_key: str) -> None:
    with _LOCK:
        _PROVIDER_FAILURES.pop(provider_key, None)
        _BACKOFF_UNTIL.pop(provider_key, None)


def disk_cache_disabled() -> bool:
    return os.environ.get("PYC_HERMES_WEB_SEARCH_DISABLE_CACHE", "").strip().lower() in {"1", "true", "yes", "on"}


def cache_file_path(cache_dir: Path, *, provider: str, query: str, max_results: int) -> Path:
    key = hashlib.sha256(f"{provider}\n{query.strip().lower()}\n{max_results}".encode("utf-8")).hexdigest()
    return cache_dir / f"{key}.json"


def read_disk_cache(cache_path: Path) -> dict[str, Any] | None:
    if disk_cache_disabled() or not cache_path.is_file():
        return None

    raw_ttl = cache_ttl_seconds()
    if raw_ttl <= 0:
        return None

    try:
        blob = cache_path.read_text(encoding="utf-8")
        data = json.loads(blob)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None

    if not isinstance(data, dict):
        return None
    expires = data.get("_cache_expires_at_unix")
    if not isinstance(expires, (int, float)) or time.time() > float(expires):
        try:
            cache_path.unlink(missing_ok=True)
        except OSError:
            pass
        return None

    payload = data.get("payload")
    return payload if isinstance(payload, dict) else None


def write_disk_cache(cache_path: Path, payload: dict[str, Any]) -> None:
    if disk_cache_disabled():
        return

    ttl = cache_ttl_seconds()
    if ttl <= 0:
        return

    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return

    envelope = {"_cache_expires_at_unix": time.time() + ttl, "payload": payload}
    tmp = cache_path.with_suffix(cache_path.suffix + ".tmp")
    try:
        tmp.write_text(json.dumps(envelope, ensure_ascii=True), encoding="utf-8")
        tmp.replace(cache_path)
    except OSError:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass



def reset_web_search_runtime_state_for_tests() -> None:
    """Reset quotas/circuit trackers (pytest hook only)."""

    global _MINUTE_SLOT, _MINUTE_USES, _HOUR_SLOT, _HOUR_USES

    global _PROVIDER_FAILURES, _BACKOFF_UNTIL

    with _LOCK:
        _MINUTE_SLOT = -1
        _MINUTE_USES = 0
        _HOUR_SLOT = -1
        _HOUR_USES = 0

        _PROVIDER_FAILURES.clear()

        _BACKOFF_UNTIL.clear()


def merge_meta(base: dict[str, Any], extra: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    nested = merged.get("meta")
    meta: dict[str, Any]
    if isinstance(nested, dict):
        meta = dict(nested)
        meta.update(extra)
    else:
        meta = dict(extra)
    merged["meta"] = meta
    return merged
