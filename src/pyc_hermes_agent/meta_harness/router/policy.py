"""Configurable routing weights for MetaHarness method selection.

``meta_routing`` overlay keys (all optional):

- ``keyword_boosts``, ``pin_method`` / ``forced_method``, scalar tuning keys
  (``dependency_penalty_per_missing``, ``language_boost_points``, ``evidence_grade_match_points``).
- ``data_shape_bonus``: ``{ "<capability_id>": <int>, ... }`` — **extra** points added on top of the
  built-in data-key rules from ``default_data_shape_bonus`` (same request ``data`` keys). Values from
  the request overlay are **summed** with any base policy ``data_shape_bonus``, including repeated ids.
- ``data_shape_rules``: list of objects describing extra points when payload keys match:

  - ``capability_id`` (str, required)
  - ``points`` (int, required)
  - ``any_keys`` (optional list): bonus applies if **at least one** listed key exists in ``request.data``
  - ``all_keys`` (optional list): bonus applies if **every** listed key exists

  At least one of ``any_keys`` or ``all_keys`` must be non-empty. If both are set, **both** conditions
  must hold. Multiple rules for the same capability all contribute (sum) when they match.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from pyc_hermes_agent.contracts import MetaAnalysisRequest

_BUILTIN_KEYWORD_BOOSTS: dict[str, tuple[str, ...]] = {
    "A-12-SCM": ("causal", "因果", "instrument", "backdoor", "did"),
    "A-12-FORECAST": ("forecast", "predict", "预测", "time series", "时序"),
    # A-13/A-14/A-15 removed: org_personal_adapters live only in standalone
    # pyc-MetaFramework. Re-enable when bridge supports lazy adapter loading.
    "A-18": ("complex", "emergence", "复杂系统", "涌现", "entropy"),
    "A-22": ("network", "传播", "拓扑", "pagerank", "percolation"),
    "A-23": ("agent-based", "abm", "schelling", "opinion", "智能体"),
}


def _coerce_tokens(raw: Any) -> tuple[str, ...]:
    if raw is None:
        return ()
    if isinstance(raw, (list, tuple)):
        return tuple(str(x).lower() for x in raw)
    return (str(raw).lower(),)


def default_data_shape_bonus(capability_id: str, data_keys: set[str]) -> int:
    if capability_id == "A-12-FORECAST" and ("series" in data_keys or "time_series" in data_keys):
        return 3
    if capability_id == "A-12-SCM" and {"df", "cause", "effect"}.issubset(data_keys):
        return 3
    if capability_id == "A-22" and ({"adjacency", "adjacency_matrix"} & data_keys):
        return 6
    if capability_id == "A-18" and "micro_states" in data_keys:
        return 3
    if capability_id == "A-23" and "agents" in data_keys:
        return 3
    return 0


def default_params_bonus(capability_id: str, params: dict[str, Any]) -> int:
    if capability_id == "A-22" and str(params.get("analysis", "")).lower() in ("pagerank", "percolation", "sir"):
        return 3
    return 0


def _coerce_str_key_list(raw: Any) -> tuple[str, ...]:
    if raw is None:
        return ()
    if isinstance(raw, (list, tuple)):
        return tuple(str(k) for k in raw if k is not None and str(k))
    return (str(raw),)


@dataclass(frozen=True, slots=True)
class DataShapeRule:
    """Declarative payload-key matcher wired from ``meta_routing["data_shape_rules"]``."""

    capability_id: str
    points: int
    any_keys: tuple[str, ...] = ()
    all_keys: tuple[str, ...] = ()

    def matches(self, data_keys: set[str]) -> bool:
        norm = {str(k) for k in data_keys}
        if self.any_keys and not (norm & set(self.any_keys)):
            return False
        if self.all_keys and not set(self.all_keys).issubset(norm):
            return False
        return True


def _coerce_data_shape_rule(raw: Any) -> DataShapeRule | None:
    if not isinstance(raw, dict):
        return None
    cap = str(raw.get("capability_id", "")).strip()
    if not cap:
        return None
    pts_raw = raw.get("points")
    if pts_raw is None or isinstance(pts_raw, bool) or not isinstance(pts_raw, (int, float)):
        return None
    any_k = _coerce_str_key_list(raw.get("any_keys"))
    all_k = _coerce_str_key_list(raw.get("all_keys"))
    if not any_k and not all_k:
        return None
    return DataShapeRule(capability_id=cap, points=int(pts_raw), any_keys=any_k, all_keys=all_k)


@dataclass(slots=True)
class MethodRoutingPolicy:
    """Scoring knobs for ``MethodSelector``; use ``builtin()`` for shipping defaults."""

    keyword_boosts: dict[str, tuple[str, ...]]
    language_boost_points: int = 5
    evidence_grade_match_points: int = 1
    dependency_penalty_per_missing: int = 4
    data_shape_bonus: dict[str, int] = field(default_factory=dict)
    data_shape_rules: tuple[DataShapeRule, ...] = ()

    @classmethod
    def builtin(cls) -> MethodRoutingPolicy:
        return cls(keyword_boosts=dict(_BUILTIN_KEYWORD_BOOSTS))

    def with_request_overlay(self, request: MetaAnalysisRequest) -> MethodRoutingPolicy:
        return self.with_overlay(getattr(request, "meta_routing", None))

    def with_overlay(self, meta_routing: Mapping[str, Any] | None) -> MethodRoutingPolicy:
        if not meta_routing:
            return self

        merged_kw = dict(self.keyword_boosts)
        boosts_extra = meta_routing.get("keyword_boosts")
        if isinstance(boosts_extra, dict) and boosts_extra:
            for cap_id, tokens in boosts_extra.items():
                tid = str(cap_id)
                extra = _coerce_tokens(tokens)
                if tid in merged_kw:
                    merged_kw[tid] = merged_kw[tid] + extra
                else:
                    merged_kw[tid] = extra

        pen = self.dependency_penalty_per_missing
        raw_pen = meta_routing.get("dependency_penalty_per_missing")
        if isinstance(raw_pen, int) and not isinstance(raw_pen, bool):
            pen = raw_pen

        lang_pts = self.language_boost_points
        raw_lang = meta_routing.get("language_boost_points")
        if isinstance(raw_lang, int) and not isinstance(raw_lang, bool):
            lang_pts = raw_lang

        ev_pts = self.evidence_grade_match_points
        raw_ev = meta_routing.get("evidence_grade_match_points")
        if isinstance(raw_ev, int) and not isinstance(raw_ev, bool):
            ev_pts = raw_ev

        merged_ds = dict(self.data_shape_bonus)
        raw_ds = meta_routing.get("data_shape_bonus")
        if isinstance(raw_ds, dict) and raw_ds:
            for cap_id, pts in raw_ds.items():
                if isinstance(pts, bool):
                    continue
                if isinstance(pts, (int, float)):
                    tid = str(cap_id)
                    merged_ds[tid] = merged_ds.get(tid, 0) + int(pts)

        merged_rules = list(self.data_shape_rules)
        raw_rules = meta_routing.get("data_shape_rules")
        if isinstance(raw_rules, list):
            for item in raw_rules:
                parsed = _coerce_data_shape_rule(item)
                if parsed is not None:
                    merged_rules.append(parsed)

        return MethodRoutingPolicy(
            keyword_boosts=merged_kw,
            language_boost_points=lang_pts,
            evidence_grade_match_points=ev_pts,
            dependency_penalty_per_missing=pen,
            data_shape_bonus=merged_ds,
            data_shape_rules=tuple(merged_rules),
        )

    def data_shape_score(self, capability_id: str, data_keys: set[str]) -> int:
        base = default_data_shape_bonus(capability_id, data_keys) + self.data_shape_bonus.get(capability_id, 0)
        rules_pts = sum(rule.points for rule in self.data_shape_rules if rule.capability_id == capability_id and rule.matches(data_keys))
        return base + rules_pts

    def language_bonus(self, capability_id: str, text_lower: str) -> int:
        tokens = self.keyword_boosts.get(capability_id, ())
        if any(tok in text_lower for tok in tokens):
            return self.language_boost_points
        return 0

    def evidence_target_bonus(self, request: MetaAnalysisRequest, capability_max_evidence: str) -> int:
        if request.target_evidence_grade in ("CE-C3", "CE-C4") and capability_max_evidence in ("CE-C3", "CE-C4"):
            return self.evidence_grade_match_points
        return 0


def routing_pin_method_id(request: MetaAnalysisRequest) -> str | None:
    routing = getattr(request, "meta_routing", None) or {}
    if not isinstance(routing, dict):
        return None
    pin = routing.get("pin_method")
    if not pin:
        pin = routing.get("forced_method")
    if isinstance(pin, str) and pin.strip():
        return pin.strip()
    return None
