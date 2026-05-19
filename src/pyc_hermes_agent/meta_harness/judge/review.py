"""Logic and reasonableness review based on MetaFramework V4.5.0 methodology."""

from __future__ import annotations

import re
from typing import Optional

from pyc_hermes_agent.contracts import CapabilityDescriptor, MetaAnalysisRequest

# Overclaim indicator words mapped to minimum grade required
_CAUSAL_WORDS = re.compile(
    r"\b(proves?|causes?|guarantees?|ensures?|intervention effect|causal impact)\b",
    re.IGNORECASE,
)
_INTERVENTION_WORDS = re.compile(
    r"\b(recommend intervention|policy effect|treatment effect)\b",
    re.IGNORECASE,
)


class MethodJudge:
    """Logic and reasonableness reviewer based on MetaFramework V4.5.0 methodology."""

    _GRADE_CLAIMS: dict[str, dict[str, str]] = {
        "CE-C1": {"can_claim": "correlation/prediction", "cannot_claim": "causation, intervention effect"},
        "CE-C2": {"can_claim": "directional association, temporal precedence", "cannot_claim": "causal mechanism, intervention recommendation"},
        "CE-C3": {"can_claim": "identified causal effect under model assumptions", "cannot_claim": "universal generalization, policy guarantee"},
        "CE-C4": {"can_claim": "causal effect with quasi-experimental support", "cannot_claim": "external validity beyond study population"},
    }

    _GRADE_RANK: dict[str, int] = {"CE-C1": 1, "CE-C2": 2, "CE-C3": 3, "CE-C4": 4}

    _REQUIRED_DATA_SHAPES: dict[str, dict] = {
        "A-22": {"required": ["adjacency", "adjacency_matrix", "edges"], "analysis_types": ["pagerank", "percolation", "cascade", "sir_network"]},
        "A-12-FORECAST": {"required": ["series", "time_series", "values"], "min_observations": 10},
        "A-12-SCM": {"required": ["treatment", "endogenous", "outcome"], "identification": ["instruments", "controls", "dag_edges"]},
        "A-23": {"required": ["agents", "agent_count", "population"], "config": ["parameters", "breeds"]},
        "A-18": {"required": ["micro_states", "state_space", "states"]},
    }

    _SAMPLE_SIZE_RULES: dict[str, int] = {
        "A-12-FORECAST": 10,
        "A-12-SCM": 30,
        "A-22": 3,
        "A-23": 10,
        "A-18": 5,
    }

    def logic_review(self, request: MetaAnalysisRequest, selected: Optional[CapabilityDescriptor]) -> list[str]:
        """Check logical consistency: data adequacy, evidence ceiling, overclaim detection."""
        if selected is None:
            return ["No methodology selected; logic review cannot proceed."]

        findings: list[str] = []
        grade = selected.max_evidence_grade or "CE-C1"
        data = getattr(request, "data", None) or {}
        params = getattr(request, "params", None) or {}
        problem = getattr(request, "problem_statement", "") or ""

        # 1. Overclaim detection
        grade_rank = self._GRADE_RANK.get(grade, 1)
        if _CAUSAL_WORDS.search(problem) and grade_rank < 3:
            findings.append(
                f"OVERCLAIM: Problem statement uses causal language but method {selected.id} "
                f"has ceiling {grade} which can only claim: {self._GRADE_CLAIMS[grade]['can_claim']}."
            )
        if _INTERVENTION_WORDS.search(problem) and grade_rank < 3:
            findings.append(
                f"OVERCLAIM: Intervention-grade language detected but {grade} cannot claim "
                f"intervention effect. Minimum CE-C3 required."
            )

        # 2. Data shape adequacy
        method_id = selected.id or ""
        shape_spec = self._REQUIRED_DATA_SHAPES.get(method_id)
        if shape_spec is not None:
            required_keys = shape_spec.get("required", [])
            data_keys = set(data.keys()) | set(params.keys())
            if not any(k in data_keys for k in required_keys):
                findings.append(
                    f"DATA MISSING: Method {method_id} requires at least one of "
                    f"{required_keys} in request data; none found."
                )
            id_keys = shape_spec.get("identification")
            if id_keys and not any(k in data_keys for k in id_keys):
                findings.append(
                    f"IDENTIFICATION MISSING: Method {method_id} requires identification "
                    f"strategy via one of {id_keys}; none found."
                )

        # 3. CE/SR separation
        if grade_rank >= 3:
            findings.append(
                "CE/SR BOUNDARY: CE-grade outputs describe methodological support only; "
                "SR certification requires a separate grading path."
            )

        # 4. Evidence ceiling annotation
        findings.append(
            f"Method {selected.id} ceiling is {grade}: "
            f"can claim {self._GRADE_CLAIMS.get(grade, {}).get('can_claim', 'unknown')}; "
            f"cannot claim {self._GRADE_CLAIMS.get(grade, {}).get('cannot_claim', 'unknown')}."
        )

        return findings

    def reasonableness_review(self, request: MetaAnalysisRequest, selected: Optional[CapabilityDescriptor]) -> list[str]:
        """Check reasonableness: sample size, domain applicability, escalation guards."""
        if selected is None:
            return ["No methodology selected; reasonableness review cannot assess adequacy."]

        findings: list[str] = []
        data = getattr(request, "data", None) or {}
        params = getattr(request, "params", None) or {}
        getattr(request, "problem_statement", "") or ""
        method_id = selected.id or ""
        grade = selected.max_evidence_grade or "CE-C1"

        # 1. Sample size check
        min_n = self._SAMPLE_SIZE_RULES.get(method_id)
        if min_n is not None:
            n = None
            for key in ("n", "sample_size", "observations", "length", "agent_count"):
                val = data.get(key) or params.get(key)
                if val is not None:
                    try:
                        n = int(val)
                    except (TypeError, ValueError):
                        pass
                    break
            if n is not None and n < min_n:
                findings.append(
                    f"SAMPLE SIZE: Method {method_id} recommends n>={min_n} "
                    f"but data indicates n={n}. Results may be unreliable."
                )
            elif n is None:
                # Check array-like data lengths
                for key in ("series", "time_series", "values", "agents", "states"):
                    val = data.get(key) or params.get(key)
                    if isinstance(val, (list, tuple)) and len(val) < min_n:
                        findings.append(
                            f"SAMPLE SIZE: {key} has {len(val)} elements; "
                            f"method {method_id} recommends >={min_n}."
                        )
                        break

        # 2. Predictive escalation guard
        grade_rank = self._GRADE_RANK.get(grade, 1)
        if grade_rank <= 2:
            findings.append(
                f"ESCALATION GUARD: {grade} outputs are predictive/observational. "
                "Must not be escalated to intervention-grade claims without CE-C3+ evidence."
            )

        # 3. Domain applicability heuristic
        shape_spec = self._REQUIRED_DATA_SHAPES.get(method_id)
        if shape_spec and "analysis_types" in shape_spec:
            analysis = params.get("analysis_type") or data.get("analysis_type")
            valid_types = shape_spec["analysis_types"]
            if analysis and analysis not in valid_types:
                findings.append(
                    f"DOMAIN: analysis_type '{analysis}' not in recognized set "
                    f"{valid_types} for method {method_id}."
                )

        # 4. Effect magnitude warning for causal methods
        if grade_rank >= 3 and not any(
            k in (set(data.keys()) | set(params.keys()))
            for k in ("effect_size", "confidence_interval", "p_value", "ate")
        ):
            findings.append(
                f"REASONABLENESS: Causal method {method_id} should report effect size "
                "and confidence intervals for result interpretation."
            )

        if not findings:
            findings.append(
                f"Method {method_id} appears reasonable for the stated problem given available data."
            )

        return findings
