"""Structural / representational (SR) grading separate from causal evidence (CE)."""

from __future__ import annotations

import re
from typing import Any, Optional

from pyc_hermes_agent.contracts import CapabilityDescriptor, MetaAnalysisRequest
from pyc_hermes_agent.meta_harness.quality.checks import request_has_overclaim_language


class SrGradingPolicy:
    """Maps run context to an SR label; optional explicit ``target_sr_grade`` on the request."""

    def grade(
        self,
        request: MetaAnalysisRequest,
        selected: Optional[CapabilityDescriptor],
        degraded: bool,
        execution_details: dict[str, Any],
    ) -> str:
        override = (getattr(request, "target_sr_grade", "") or "").strip()
        if override:
            matched = re.fullmatch(r"SR-C(\d+)", override.upper())
            if matched:
                return f"SR-C{matched.group(1)}"

        if degraded or selected is None:
            return "SR-C2"
        if request_has_overclaim_language(request):
            return "SR-C2"

        status = execution_details.get("status")
        if status and status != "not_run":
            if execution_details.get("error") or execution_details.get("validated") is False:
                return "SR-C2"

        return "SR-C1"
