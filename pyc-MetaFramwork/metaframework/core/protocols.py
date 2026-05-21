"""Protocols shared by engines and execution layer."""

from __future__ import annotations

from typing import Any, Dict, Protocol


class EngineProtocol(Protocol):
    def execute(self, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        ...
