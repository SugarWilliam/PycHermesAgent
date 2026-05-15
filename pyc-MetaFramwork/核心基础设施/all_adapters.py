"""Climate dynamics adapter: radiative forcing, ECS, damage function."""
from __future__ import annotations

import logging
from typing import Any, Dict

import numpy as np

from forecast_adapters import ForecastAdapter, BSTSAdapter, SyntheticControlAdapter
from org_personal_adapters import OrganizationAdapter, PersonalGrowthAdapter, TeamManagementAdapter
from complex_systems_adapters import (
    TippingAdapter, SOCAdapter, CausalEmergenceAdapter,
    TransferEntropyAdapter, EvolutionaryAdapter, CoarseGrainingAdapter,
)
from network_science_adapters import NetworkScienceAdapter
from abm_adapter_v450 import ABMAdapter

logger = logging.getLogger("metamodel.adapters.climate")


class ClimateAdapter:
    """A-03: Climate Dynamics Adapter."""

    adapter_id = "A-03"
    version = "4.0.0"
    disciplines = ["Climate Dynamics"]
    theories = ["Myhre (1998) Radiative Forcing", "Arrhenius Climate Sensitivity", "IPCC AR6"]

    def __call__(self, *, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        co2 = np.asarray(data.get("co2_ppm", []), dtype=float)
        if len(co2) == 0:
            raise ValueError("No CO2 data provided")

        co2_base = params.get("co2_preindustrial", 280.0)
        ecs = params.get("ecs", 3.0)

        # Radiative forcing
        forcing = 5.35 * np.log(co2 / co2_base)

        # Climate sensitivity parameter
        lambda_cs = ecs / (5.35 * np.log(2))

        # Equilibrium and transient temperature
        temp_eq = lambda_cs * forcing
        temp_tr = temp_eq * params.get("transient_fraction", 0.67)

        return {
            "forcing": forcing.tolist(),
            "temperature_equilibrium": temp_eq.tolist(),
            "temperature_transient": temp_tr.tolist(),
            "lambda": float(lambda_cs),
            "ecs": float(ecs),
            "co2_base": co2_base,
            "model": "Myhre-Arrhenius",
            "validated": True,
            "adapter_id": self.adapter_id,
        }


class ExtremeValueAdapter:
    """A-03-EVT: Extreme Value Theory adapter."""

    adapter_id = "A-03-EVT"
    version = "4.0.0"
    disciplines = ["Climate Dynamics", "Risk Analysis"]
    theories = ["GEV Distribution", "Return Level Analysis"]

    def __call__(self, *, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        from scipy.stats import genextreme as gev

        series = np.asarray(data.get("series", []), dtype=float)
        if len(series) < 10:
            raise ValueError("Need at least 10 observations for EVT")

        gev_params = gev.fit(series)
        shape, loc, scale = gev_params

        return_periods = params.get("return_periods", [10, 50, 100])
        return_levels = {}
        for rp in return_periods:
            p = 1 - 1 / rp
            return_levels[rp] = float(gev.ppf(p, *gev_params))

        prob_exceed = 1 - gev.cdf(np.max(series), *gev_params)

        return {
            "gev_shape": float(shape),
            "gev_loc": float(loc),
            "gev_scale": float(scale),
            "return_levels": return_levels,
            "prob_exceed_current": float(prob_exceed),
            "current_max": float(np.max(series)),
            "model": "GEV-EVT",
            "validated": True,
            "adapter_id": self.adapter_id,
        }


class EpidemiologyAdapter:
    """A-07-E: Epidemiological dynamics with time-varying transmission."""

    adapter_id = "A-07-E"
    version = "4.0.0"
    disciplines = ["Epidemiology"]
    theories = ["SEIR with time-varying beta", "Wallinga-Teunis Rt estimation"]

    def __call__(self, *, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        cases = np.asarray(data.get("cases", []), dtype=float)
        if len(cases) == 0:
            raise ValueError("No case data provided")

        R0 = params.get("R0", 2.5)
        serial_interval = params.get("serial_interval", 5.2)
        policy_effect = params.get("policy_effect", 0.0)
        stringency = np.asarray(data.get("stringency", np.zeros(len(cases))), dtype=float)

        gamma = 1.0 / serial_interval

        # CORRECTED: policy_effect actually reduces transmission
        if len(stringency) == len(cases) and policy_effect > 0:
            reduction = policy_effect * (stringency / 100.0)
            R_t = R0 * np.exp(-reduction)
        else:
            R_t = np.full(len(cases), R0, dtype=float)

        # Estimate Rt from case data (Cori simplified)
        window = max(3, int(serial_interval / 2))
        Rt_est = np.full(len(cases), np.nan)
        for i in range(window, len(cases)):
            if cases[i - window] > 0 and cases[i] > 0:
                ratio = cases[i] / cases[i - window]
                Rt_est[i] = ratio ** (serial_interval / window)
        Rt_est = np.clip(Rt_est, 0.1, 10.0)

        mask_high = stringency > 50 if len(stringency) == len(cases) else np.full(len(cases), False)
        mask_low = stringency < 30 if len(stringency) == len(cases) else np.full(len(cases), False)

        Rt_controlled = np.nanmean(Rt_est[mask_high]) if np.any(mask_high) else np.nanmean(Rt_est)
        Rt_uncontrolled = np.nanmean(Rt_est[mask_low]) if np.any(mask_low) else np.nanmean(Rt_est)

        return {
            "R0": float(R0),
            "gamma": float(gamma),
            "Rt_estimated": np.nan_to_num(Rt_est, nan=-1.0).tolist(),
            "Rt_mean": float(np.nanmean(Rt_est)),
            "Rt_controlled": float(Rt_controlled),
            "Rt_uncontrolled": float(Rt_uncontrolled),
            "R_t_model": R_t.tolist(),
            "policy_effect_applied": float(policy_effect),
            "herd_immunity_threshold": float(1 - 1 / R0),
            "model": "SEIR-time-varying",
            "validated": True,
            "adapter_id": self.adapter_id,
        }


class CognitionAdapter:
    """A-07-B: Cognitive risk perception adapter."""

    adapter_id = "A-07-B"
    version = "4.0.0"
    disciplines = ["Cognitive Science"]
    theories = ["Slovic Psychometric Model", "Prospect Theory (Kahneman)"]

    def __call__(self, *, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        cases = np.asarray(data.get("cases", []), dtype=float)
        population = params.get("population", 1.0)
        kappa = params.get("loss_aversion", 2.25)

        incidence = cases / population * 1e5  # per 100k
        # Normalize to 0-1 scale using 95th percentile
        p95 = np.percentile(incidence, 95) if np.any(incidence > 0) else 1.0
        dread = np.clip(incidence / p95, 0, 1)
        unknown = np.exp(-incidence / (p95 * 0.5 + 1e-6))
        perceived_risk = 0.6 * dread + 0.4 * unknown
        perceived_loss = kappa * perceived_risk

        return {
            "incidence_per_100k": incidence.tolist(),
            "dread_component": dread.tolist(),
            "unknown_component": unknown.tolist(),
            "perceived_risk": perceived_risk.tolist(),
            "perceived_loss": perceived_loss.tolist(),
            "loss_aversion": float(kappa),
            "model": "Slovic-Prospect",
            "validated": True,
            "adapter_id": self.adapter_id,
        }


class PolicyFeedbackAdapter:
    """A-07-A: Policy feedback / reverse causality adapter."""

    adapter_id = "A-07-A"
    version = "4.0.0"
    disciplines = ["Social Dynamics"]
    theories = ["Feedback Control", "Policy Response Lag"]

    def __call__(self, *, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        from stats_module import CausalityTester

        cases = np.asarray(data.get("cases", []), dtype=float)
        stringency = np.asarray(data.get("stringency", []), dtype=float)
        lag_days = int(params.get("lag_days", 14))
        granularity = params.get("granularity", "daily")  # or "weekly"

        # Use log growth of cases
        with np.errstate(divide="ignore"):
            case_growth = np.log(cases + 1)
        case_growth = np.diff(case_growth)

        if len(case_growth) <= lag_days or len(stringency) <= lag_days:
            return {
                "reverse_slope": 0.0,
                "reverse_pvalue": 1.0,
                "policy_responds_to_cases": False,
                "lag_days": lag_days,
                "model": "Feedback-control",
                "validated": False,
                "adapter_id": self.adapter_id,
                "warning": "Insufficient data for lag analysis",
            }

        future_stringency = stringency[lag_days:]
        current_growth = case_growth[: len(future_stringency)]

        # Use causality tester with stationarity handling
        ct = CausalityTester()
        result = ct.granger(future_stringency, current_growth, lags=2, make_stationary=True)

        return {
            "reverse_slope": float(result["f_stat"]),
            "reverse_pvalue": float(result["p_value"]),
            "policy_responds_to_cases": result["significant"],
            "lag_days": lag_days,
            "model": "Feedback-control",
            "validated": True,
            "adapter_id": self.adapter_id,
        }


class EconometricsAdapter:
    """A-12-A: Econometrics adapter (cointegration + Granger + ECM)."""

    adapter_id = "A-12-A"
    version = "4.0.0"
    disciplines = ["Econometrics"]
    theories = ["Johansen Cointegration", "Granger Causality", "Error Correction Model"]

    def __call__(self, *, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        from stats_module import CausalityTester, CointegrationTester

        y = np.asarray(data.get("y", []), dtype=float)
        x = np.asarray(data.get("x", []), dtype=float)
        lags = int(params.get("lags", 2))

        # Cointegration test
        ct_int = CointegrationTester()
        coint = ct_int.engle_granger(y, x)

        # Granger causality with stationarity handling
        ct_caus = CausalityTester()
        granger_y_x = ct_caus.granger(y, x, lags=lags, make_stationary=True)
        granger_x_y = ct_caus.granger(x, y, lags=lags, make_stationary=True)

        return {
            "cointegration": coint,
            "granger_y_to_x": granger_y_x,
            "granger_x_to_y": granger_x_y,
            "long_run_slope": float(coint["slope"]),
            "long_run_r2": float(coint["r_squared"]),
            "is_cointegrated": bool(coint["cointegrated"]),
            "model": "ECM-Granger-Cointegration",
            "validated": True,
            "adapter_id": self.adapter_id,
        }


class EnergyEconomicsAdapter:
    """A-12-F: Energy economics / decoupling adapter."""

    adapter_id = "A-12-F"
    version = "4.0.0"
    disciplines = ["Energy Economics"]
    theories = ["Tapio Decoupling", "Kaya Identity"]

    def __call__(self, *, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        co2 = np.asarray(data.get("co2", []), dtype=float)
        gdp = np.asarray(data.get("gdp", []), dtype=float)

        if len(co2) < 2 or len(gdp) < 2:
            raise ValueError("Need at least 2 observations for decoupling analysis")

        with np.errstate(divide="ignore", invalid="ignore"):
            co2_growth = np.diff(co2) / co2[:-1] * 100
            gdp_growth = np.diff(gdp) / gdp[:-1] * 100
            co2_growth = np.nan_to_num(co2_growth, nan=0, posinf=0, neginf=0)
            gdp_growth = np.nan_to_num(gdp_growth, nan=0, posinf=0, neginf=0)

        # Tapio elasticity
        valid = np.abs(gdp_growth) > 1e-6
        if np.any(valid):
            elasticity = np.mean(co2_growth[valid] / gdp_growth[valid])
        else:
            elasticity = 0.0

        decoupling_type = (
            "strong" if elasticity < 0 else
            "weak" if elasticity < 0.8 else
            "expansive"
        )

        return {
            "decoupling_elasticity": float(elasticity),
            "decoupling_type": decoupling_type,
            "co2_growth_mean": float(np.mean(co2_growth)),
            "gdp_growth_mean": float(np.mean(gdp_growth)),
            "carbon_intensity": (co2 / gdp).tolist(),
            "model": "Tapio-Kaya",
            "validated": True,
            "adapter_id": self.adapter_id,
        }


class DamageFunctionAdapter:
    """A-12-G: Climate damage function adapter (Nordhaus DICE)."""

    adapter_id = "A-12-G"
    version = "4.0.0"
    disciplines = ["Risk / Insurance", "Climate Economics"]
    theories = ["Nordhaus DICE-2016R", "Quadratic Damage Function"]

    def __call__(self, *, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        temperature = np.asarray(data.get("temperature", 0.0), dtype=float)
        if temperature.ndim == 0:
            temperature = np.array([temperature])
        gdp_baseline = params.get("gdp_baseline", 1.0)
        alpha = params.get("damage_coefficient", 0.00236)
        beta = params.get("damage_denominator", 0.0)  # 0 = pure quadratic

        if beta > 0:
            damage_fraction = alpha * temperature**2 / (1 + beta * temperature**2)
        else:
            damage_fraction = alpha * temperature**2
        damage_fraction = np.clip(damage_fraction, 0, 0.99)

        residual_gdp = gdp_baseline * (1 - damage_fraction)

        return {
            "damage_fraction": damage_fraction.tolist(),
            "damage_percent": (damage_fraction * 100).tolist(),
            "residual_gdp": residual_gdp.tolist(),
            "gdp_loss": (gdp_baseline * damage_fraction).tolist(),
            "coefficient": float(alpha),
            "model": "Nordhaus-DICE",
            "validated": True,
            "adapter_id": self.adapter_id,
        }


# ============================================================
# v4.3.1 Patch: SCMAdapter — Structural Causal Model (C3/C4)
# 与 A-12-A Granger 并列，不替代。零侵入现有代码。
# ============================================================
class SCMAdapter:
    """A-12-SCM: Structural Causal Model Adapter (C3/C4级别)"""

    adapter_id = "A-12-SCM"
    version = "4.3.1"
    disciplines = ["因果推断", "计量经济学"]
    theories = ["Pearl(2009) SCM", "2SLS (Angrist & Pischke)", "IPW (Rubin)"]

    def __call__(self, *, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """统一的适配器入口，兼容 MetaFramework.call()"""
        from structural_causal import StructuralCausalAnalyzer

        df = data.get("df")
        cause = data.get("cause")
        effect = data.get("effect")
        graph = data.get("graph")
        instrument = data.get("instrument")
        known_confounders = params.get("known_confounders")
        method = params.get("method", "auto")

        # 防御：缺失必要字段时优雅降级
        if df is None or cause is None or effect is None:
            return {
                "cause": cause, "effect": effect,
                "identification": "error",
                "estimate": np.nan, "ci_lower": np.nan, "ci_upper": np.nan,
                "p_value": 1.0, "method": "none", "causal_grade": "C2",
                "warning": "Missing df/cause/effect for SCM. Pass them in data dict.",
                "model": "Pearl-SCM", "validated": False,
                "adapter_id": self.adapter_id,
            }

        try:
            analyzer = StructuralCausalAnalyzer()
            result = analyzer.estimate_causal_effect(
                df, cause, effect, graph=graph,
                known_confounders=known_confounders,
                instrument=instrument, method=method
            )

            # 反驳检验（仅当达到C3时执行）
            sensitivity = None
            if result.causal_grade in ["C3", "C3+"]:
                try:
                    sensitivity = analyzer.sensitivity_analysis(result, df)
                except Exception as e:
                    sensitivity = {"error": str(e)}

            return {
                "cause": result.cause,
                "effect": result.effect,
                "identification": result.identification,
                "estimate": result.estimate,
                "ci_lower": result.ci_lower,
                "ci_upper": result.ci_upper,
                "p_value": result.p_value,
                "method": result.method,
                "causal_grade": result.causal_grade,
                "refutation_passed": result.refutation_passed,
                "sensitivity": sensitivity,
                "warning": result.warning,
                "model": "Pearl-SCM-2SLS",
                "validated": True,
                "adapter_id": self.adapter_id,
            }

        except Exception as e:
            return {
                "cause": cause, "effect": effect,
                "identification": "error",
                "estimate": np.nan, "ci_lower": np.nan, "ci_upper": np.nan,
                "p_value": 1.0, "method": "none", "causal_grade": "C2",
                "warning": f"SCM estimation failed: {str(e)}",
                "model": "Pearl-SCM", "validated": False,
                "adapter_id": self.adapter_id,
            }
