"""Utility helpers, surface building, skill/tool discovery, and text parsing."""

from __future__ import annotations

import ast
from pathlib import Path
import re

from pyc_hermes_agent.contracts import (
    HermesSkillDescriptor,
    HermesSurface,
    HermesRuntimeSnapshot,
    HermesIntegrationSnapshot,
)

from .constants import (
    _PlaceholderSpec,
    _SurfaceSpec,
    _SKILLS_PLACEHOLDER,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _read_text(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _search_value(pattern: str, text: str) -> str:
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        return ""
    return match.group(1).strip()


def _literal_str(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _literal_str_list(node: ast.AST) -> list[str]:
    if not isinstance(node, (ast.List, ast.Tuple)):
        return []
    values: list[str] = []
    for element in node.elts:
        value = _literal_str(element)
        if value is not None:
            values.append(value)
    return values


def _surface_lookup(snapshot: HermesRuntimeSnapshot) -> dict[str, HermesSurface]:
    return {surface.id: surface for surface in snapshot.surfaces}


def _build_surface(spec: _SurfaceSpec, upstream_root: Path) -> HermesSurface:
    return HermesSurface(
        id=spec.id,
        kind=spec.kind,
        path=spec.relative_path,
        available=(upstream_root / spec.relative_path).exists(),
        required=spec.required,
    )


def _detect_entrypoints(upstream_root: Path, source_paths: tuple[str, ...], entrypoints: tuple[str, ...]) -> list[str]:
    detected: list[str] = []
    texts = [_read_text(upstream_root / relative_path) for relative_path in source_paths]
    for entrypoint in entrypoints:
        name_pattern = re.compile(rf"^\s*(?:class|def)\s+{re.escape(entrypoint)}\b", re.MULTILINE)
        if any(name_pattern.search(text) or entrypoint in text for text in texts if text):
            detected.append(entrypoint)
    return detected


def _discover_paths(upstream_root: Path, patterns: tuple[str, ...]) -> list[str]:
    matches: list[str] = []
    for pattern in patterns:
        for path in upstream_root.glob(pattern):
            if path.is_file():
                matches.append(path.relative_to(upstream_root).as_posix())
    return sorted(_unique(matches))


def _discover_skill_paths(upstream_root: Path) -> list[Path]:
    return [upstream_root / relative_path for relative_path in _discover_paths(upstream_root, _SKILLS_PLACEHOLDER.discovery_patterns)]


def _discover_skill_roots(upstream_root: Path) -> list[str]:
    roots: list[str] = []
    for relative_path in ("skills", "optional-skills"):
        if (upstream_root / relative_path).exists():
            roots.append(relative_path)
    return roots


def _parse_frontmatter(text: str) -> tuple[dict[str, str], dict[str, str], str | None]:
    lines = text.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        return {}, {}, "Skill frontmatter missing."

    frontmatter: dict[str, str] = {}
    nested_metadata: dict[str, str] = {}
    in_metadata_block = False

    idx = 1
    while idx < len(lines):
        line = lines[idx]
        if line.strip() == "---":
            return frontmatter, nested_metadata, None

        if in_metadata_block and line.startswith("  "):
            if ":" in line:
                key, value = line.strip().split(":", 1)
                nested_metadata[key.strip()] = value.strip()
            idx += 1
            continue

        in_metadata_block = False
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if key == "metadata":
                in_metadata_block = True
            else:
                frontmatter[key] = value
        idx += 1

    return frontmatter, nested_metadata, "Skill frontmatter terminator missing."


def _derive_markdown_title(text: str, fallback: str) -> str:
    match = re.search(r"^#\s+(.+?)\s*$", text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return fallback


def _build_skill_descriptor(skill_path: Path, upstream_root: Path) -> HermesSkillDescriptor:
    relative_path = skill_path.relative_to(upstream_root).as_posix()
    parts = skill_path.relative_to(upstream_root).parts
    source = "optional" if parts and parts[0] == "optional-skills" else "bundled"
    derived_category = parts[1] if len(parts) >= 3 else ""
    descriptor_id = "/".join(parts[1:-1]) if len(parts) >= 3 else skill_path.parent.name
    text = _read_text(skill_path)
    frontmatter, metadata, parse_error = _parse_frontmatter(text)

    missing_fields: list[str] = []
    if not frontmatter.get("name"):
        missing_fields.append("name")
    if not frontmatter.get("description"):
        missing_fields.append("description")
    if missing_fields:
        parse_error = parse_error or f"Skill metadata missing required fields: {', '.join(missing_fields)}."

    return HermesSkillDescriptor(
        id=descriptor_id,
        name=frontmatter.get("name") or _derive_markdown_title(text, skill_path.parent.name),
        description=frontmatter.get("description", ""),
        path=relative_path,
        source=source,
        category=metadata.get("category") or frontmatter.get("category", derived_category),
        license=frontmatter.get("license"),
        compatibility=frontmatter.get("compatibility"),
        metadata=metadata,
        loadable=parse_error is None,
        parse_error=parse_error,
    )


def _extract_class_methods(text: str, class_name: str) -> list[str]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return [item.name for item in node.body if isinstance(item, ast.FunctionDef)]
    return []


def _extract_config_keys(text: str) -> list[str]:
    keys: list[str] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return keys
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        dict_keys = [_literal_str(key) for key in node.keys if key is not None]
        if not dict_keys:
            continue
        interesting = {"key", "description", "secret", "required", "default", "choices", "url", "env_var"}
        if interesting.intersection(dict_keys):
            for key in dict_keys:
                if key and key not in interesting:
                    keys.append(key)
    return _unique(keys)


def _build_placeholder_snapshot(spec: _PlaceholderSpec, runtime_snapshot: HermesRuntimeSnapshot) -> HermesIntegrationSnapshot:
    upstream_root = Path(runtime_snapshot.upstream_root)
    surfaces = _surface_lookup(runtime_snapshot)
    available_surfaces = [surface_id for surface_id in spec.required_surfaces if surfaces.get(surface_id) is not None and surfaces[surface_id].available]
    missing_surfaces = [surface_id for surface_id in spec.required_surfaces if surface_id not in available_surfaces]
    detected_entrypoints = _detect_entrypoints(upstream_root, spec.source_paths, spec.entrypoints)
    discovered_paths = _discover_paths(upstream_root, spec.discovery_patterns) if runtime_snapshot.checkout_present else []

    warnings: list[str] = []
    if missing_surfaces:
        warnings.append(f"Missing Hermes surfaces for {spec.surface}: {', '.join(missing_surfaces)}.")
    if not runtime_snapshot.import_ready:
        warnings.append("Hermes checkout is not import-ready; placeholder remains discovery-only.")
    if not detected_entrypoints and not missing_surfaces:
        warnings.append(f"Expected Hermes entrypoints for {spec.surface} were not detected in vendored sources.")
    warnings.extend(runtime_snapshot.warnings)

    return HermesIntegrationSnapshot(
        surface=spec.surface,
        integration_mode="discovery-only",
        status="placeholder" if not missing_surfaces else "blocked",
        placeholder=True,
        bridge_ready=False,
        upstream_available=not missing_surfaces,
        checkout_import_ready=runtime_snapshot.import_ready,
        worktree_state=runtime_snapshot.worktree_state,
        source_paths=list(spec.source_paths),
        required_surfaces=list(spec.required_surfaces),
        available_surfaces=available_surfaces,
        detected_entrypoints=detected_entrypoints,
        planned_operations=list(spec.planned_operations),
        discovered_count=len(discovered_paths),
        sample_paths=discovered_paths[:20],
        warnings=_unique(warnings),
    )
