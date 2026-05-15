"""Capability resolution and execution."""

from __future__ import annotations

from importlib import import_module
from typing import Any, Dict

from metaframework.core.errors import ExecutionError, UnknownCapabilityError
from metaframework.core.evidence import EvidenceLevel, clamp_evidence_level
from metaframework.core.result import ExecutionResult
from metaframework.core.types import ExecutionRequest
from metaframework.registry.aliases import resolve_capability_alias
from metaframework.registry.capabilities import get_capability
from metaframework.validation.contracts import validate_request_data


def execute_request(request: ExecutionRequest) -> ExecutionResult:
    resolved_capability_id = resolve_capability_alias(request.capability_id)
    spec = get_capability(resolved_capability_id)
    if spec is None:
        raise UnknownCapabilityError(f"Unknown capability: {request.capability_id}")

    missing_fields = validate_request_data(resolved_capability_id, request.data)
    if missing_fields:
        return ExecutionResult(
            capability_id=spec.capability_id,
            success=False,
            validated=False,
            payload={},
            evidence_level=spec.default_evidence,
            method=spec.display_name,
            engine=f"{spec.engine_module}.{spec.engine_class}",
            warnings=[],
            errors=[f"Missing required fields: {', '.join(missing_fields)}"],
            provenance={
                "category": spec.category,
                "tags": spec.tags,
                "required_dependencies": spec.required_dependencies,
            },
        )

    params = dict(spec.default_params)
    params.update(request.params or {})

    try:
        module = import_module(spec.engine_module)
        engine_cls = getattr(module, spec.engine_class)
        engine = engine_cls()
        payload = engine.execute(request.data, params)
    except Exception as exc:
        raise ExecutionError(f"Execution failed for {request.capability_id}: {exc}") from exc

    warnings = list(payload.get("warnings", []))
    errors = list(payload.get("errors", []))
    success = bool(payload.get("success", not errors))
    validated = bool(payload.get("validated", success and not errors))
    evidence = clamp_evidence_level(request.requested_evidence, spec.max_evidence)

    reported_evidence = payload.get("evidence_level")
    if reported_evidence is not None:
        if isinstance(reported_evidence, str):
            reported_evidence = EvidenceLevel(reported_evidence)
        evidence = clamp_evidence_level(reported_evidence, spec.max_evidence)

    return ExecutionResult(
        capability_id=spec.capability_id,
        success=success,
        validated=validated,
        payload={k: v for k, v in payload.items() if k not in {"warnings", "errors", "success", "validated", "evidence_level"}},
        evidence_level=evidence,
        method=str(payload.get("method", spec.display_name)),
        engine=f"{spec.engine_module}.{spec.engine_class}",
        warnings=warnings,
        errors=errors,
        provenance={
            "category": spec.category,
            "tags": spec.tags,
            "required_dependencies": spec.required_dependencies,
            "requested_capability_id": request.capability_id,
            "resolved_capability_id": resolved_capability_id,
        },
    )
