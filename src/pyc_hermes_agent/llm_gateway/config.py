"""opencode-style config loading and resolution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from pyc_hermes_agent.llm_gateway.resolver import resolve_llm_config
from pyc_hermes_agent.llm_gateway.types import ResolvedLLMConfig


def find_opencode_like_config(start_path: Path) -> Optional[Path]:
    current = start_path.resolve()
    if current.is_file():
        current = current.parent
    for path in [current, *current.parents]:
        for candidate in ("opencode.json", "opencode.jsonc"):
            config_path = path / candidate
            if config_path.exists():
                return config_path
    return None


def load_opencode_like_config(start_path: Path) -> Optional[Dict[str, Any]]:
    path = find_opencode_like_config(start_path)
    if path is not None:
        text = path.read_text(encoding="utf-8")
        cleaned = strip_jsonc_comments(text)
        return json.loads(cleaned)
    return None


def resolve_opencode_like_config(start_path: Path) -> ResolvedLLMConfig:
    path = find_opencode_like_config(start_path)
    raw = load_opencode_like_config(start_path) or {}
    return resolve_llm_config(raw, config_path=path)


def strip_jsonc_comments(text: str) -> str:
    result = []
    i = 0
    in_string = False
    escape = False
    while i < len(text):
        char = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""

        if in_string:
            result.append(char)
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            i += 1
            continue

        if char == '"':
            in_string = True
            result.append(char)
            i += 1
            continue

        if char == "/" and nxt == "/":
            i += 2
            while i < len(text) and text[i] not in "\r\n":
                i += 1
            continue

        if char == "/" and nxt == "*":
            i += 2
            while i + 1 < len(text) and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            continue

        result.append(char)
        i += 1

    return "".join(result)
