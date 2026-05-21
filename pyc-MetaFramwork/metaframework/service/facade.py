"""Unified MetaFramework execution facade."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict

from metaframework.core.evidence import EvidenceLevel
from metaframework.core.result import ExecutionResult
from metaframework.core.types import ExecutionRequest
from metaframework.execution.resolver import execute_request
from metaframework.registry.aliases import LEGACY_CAPABILITY_ALIASES
from metaframework.registry.capabilities import list_capabilities
from metaframework.provenance.snapshot import default_snapshot_store


class MetaFrameworkFacade:
    def describe_capability(self, capability_id: str) -> Dict[str, Any]:
        catalog = self.list_capabilities()
        resolved = capability_id
        for alias in catalog.get("aliases", []):
            if alias["alias"] == capability_id:
                resolved = alias["capability_id"]
                break
        matches = [item for item in catalog["capabilities"] if item["capability_id"] == resolved]
        if not matches:
            raise ValueError(f"Unknown capability: {capability_id}")
        return {
            "requested": capability_id,
            "resolved": resolved,
            "capability": matches[0],
        }

    def list_capabilities(self) -> Dict[str, Any]:
        capabilities = []
        for spec in list_capabilities():
            capabilities.append(
                {
                    "capability_id": spec.capability_id,
                    "display_name": spec.display_name,
                    "category": spec.category,
                    "default_evidence": spec.default_evidence.value,
                    "max_evidence": spec.max_evidence.value,
                    "engine_module": spec.engine_module,
                    "engine_class": spec.engine_class,
                    "required_dependencies": spec.required_dependencies,
                    "required_fields": spec.required_fields,
                    "tags": spec.tags,
                    "maturity": spec.maturity,
                    "status": spec.status,
                    "legacy_aliases": spec.legacy_aliases,
                    "description": spec.description,
                }
            )
        aliases = [
            {"alias": alias, "capability_id": capability_id}
            for alias, capability_id in sorted(LEGACY_CAPABILITY_ALIASES.items())
        ]
        return {
            "schema_version": "v0.1-capability-catalog",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "count": len(capabilities),
            "capabilities": capabilities,
            "aliases": aliases,
        }

    def export_capability_metadata(self, output_file: str) -> Dict[str, Any]:
        metadata = self.list_capabilities()
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        return {"success": True, "output_file": output_file, "count": metadata["count"]}

    def snapshot_result(self, request: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        return default_snapshot_store.save_execution(result=result, request=request)

    def list_snapshots(self) -> Dict[str, Any]:
        return default_snapshot_store.list_snapshots()

    def load_snapshot(self, snapshot_id: str) -> Dict[str, Any]:
        return default_snapshot_store.load_snapshot(snapshot_id)

    def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        requested_evidence = request.get("requested_evidence")
        if isinstance(requested_evidence, str):
            requested_evidence = EvidenceLevel(requested_evidence)
        execution_request = ExecutionRequest(
            capability_id=request["capability_id"],
            data=request.get("data", {}),
            params=request.get("params", {}),
            description=request.get("description", ""),
            requested_evidence=requested_evidence,
            metadata=request.get("metadata", {}),
        )
        result: ExecutionResult = execute_request(execution_request)
        result_dict = result.to_dict()
        if request.get("snapshot"):
            snapshot = self.snapshot_result(request=request, result=result_dict)
            result_dict["snapshot"] = snapshot
        return result_dict
