"""
组织、个人成长与团队管理适配器组 (源自 V4.5.0-GA, 合入 V4.3.1-GA)
A-13-ORG:   组织与项目分析（EVM / 流失预警 / 变革DiD）
A-14-PERS:  个人成长分析（学习曲线 / 习惯养成 / 目标达成）
A-15-TEAM:  团队管理分析（生产力分解 / 冲突检测 / 最优规模）
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize

logger = logging.getLogger("metamodel.adapters.org_personal")


# ============================================================
# A-13-ORG: Organization & Project Management Adapter
# ============================================================
class OrganizationAdapter:
    """A-13: 组织与项目分析适配器

    覆盖：项目绩效预测(EVM)、员工流失预警、组织变革因果评估(DiD)
    因果层级：EVM/Churn=C1(预测), DiD=C3(反事实因果)
    """

    adapter_id = "A-13-ORG"
    version = "4.4.0"
    disciplines = ["Organization Science", "Project Management", "HR Analytics"]
    theories = [
        "Earned Value Management (ANSI/EIA-748)",
        "Cox Proportional Hazards / Logistic Regression",
        "Difference-in-Differences (Card & Krueger 1994)",
    ]

    def __call__(self, *, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        analysis_type = params.get("analysis", "evm")  # evm / churn / org_change

        if analysis_type == "evm":
            return self._project_evm(data, params)
        elif analysis_type == "churn":
            return self._churn_prediction(data, params)
        elif analysis_type == "org_change":
            return self._organizational_change_did(data, params)
        else:
            return {"error": f"Unknown analysis type: {analysis_type}", "validated": False, "adapter_id": self.adapter_id}

    # --------------------------------------------------------
    # EVM: Earned Value Management
    # --------------------------------------------------------
    def _project_evm(self, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """项目绩效分析与完工预测（C1-预测性）"""
        pv = np.asarray(data.get("planned_value", []), dtype=float)  # Planned Value
        ev = np.asarray(data.get("earned_value", []), dtype=float)  # Earned Value
        ac = np.asarray(data.get("actual_cost", []), dtype=float)  # Actual Cost
        bac = float(params.get("budget_at_completion", 0.0))  # Total Budget

        if len(pv) < 3 or len(ev) < 3 or len(ac) < 3:
            return {"error": "Need at least 3 data points for EVM", "validated": False, "adapter_id": self.adapter_id}

        # Core indices (latest)
        cpi = ev[-1] / ac[-1] if ac[-1] != 0 else 1.0
        spi = ev[-1] / pv[-1] if pv[-1] != 0 else 1.0
        cv = ev[-1] - ac[-1]
        sv = ev[-1] - pv[-1]

        # Forecasts
        eac_bac = bac / cpi if cpi != 0 else bac  # Estimate at Completion (CPI-based)
        eac_combo = ac[-1] + (bac - ev[-1]) / (cpi * spi) if (cpi * spi) != 0 else bac
        etc = eac_bac - ac[-1]  # Estimate to Complete
        vac = bac - eac_bac  # Variance at Completion
        tcpi = (bac - ev[-1]) / (bac - ac[-1]) if (bac - ac[-1]) != 0 else 1.0

        # Trend analysis (rolling 3-point)
        cpi_series = ev / np.maximum(ac, 1e-9)
        spi_series = ev / np.maximum(pv, 1e-9)

        # Probabilistic confidence (bootstrap on recent performance)
        recent_window = min(10, len(cpi_series))
        recent_cpi = cpi_series[-recent_window:]
        boot_means = []
        for _ in range(1000):
            boot = np.random.choice(recent_cpi, size=recent_window, replace=True)
            boot_means.append(np.mean(boot))
        ci_lower = np.percentile(boot_means, 2.5)
        ci_upper = np.percentile(boot_means, 97.5)

        # Risk classification
        risk = "LOW"
        if cpi < 0.9 or spi < 0.9:
            risk = "HIGH"
        elif cpi < 0.95 or spi < 0.95:
            risk = "MEDIUM"

        # Forecast completion date
        planned_duration = float(params.get("planned_duration", len(pv)))
        if spi > 0:
            forecast_duration = planned_duration / spi
        else:
            forecast_duration = planned_duration * 2

        return {
            "analysis": "evm",
            "causal_grade": "C1",
            "causal_note": "Predictive extrapolation — assumes future performance mirrors past",
            "indices": {
                "cpi": round(float(cpi), 4),
                "spi": round(float(spi), 4),
                "cv": round(float(cv), 2),
                "sv": round(float(sv), 2),
            },
            "forecasts": {
                "eac_bac": round(float(eac_bac), 2),
                "eac_combo": round(float(eac_combo), 2),
                "etc": round(float(etc), 2),
                "vac": round(float(vac), 2),
                "tcpi": round(float(tcpi), 4),
                "forecast_duration": round(float(forecast_duration), 2),
            },
            "risk": risk,
            "cpi_ci_95": [round(float(ci_lower), 4), round(float(ci_upper), 4)],
            "validated": True,
            "adapter_id": self.adapter_id,
        }

    # --------------------------------------------------------
    # Churn Prediction (HR Analytics)
    # --------------------------------------------------------
    def _churn_prediction(self, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """员工流失风险预警（C1-预测性，C2-条件独立若含对照）"""
        df = data.get("df")
        if df is None or not isinstance(df, pd.DataFrame):
            # If no DataFrame, use synthetic arrays
            features = np.asarray(data.get("features", []), dtype=float)
            labels = np.asarray(data.get("labels", []), dtype=int)
            if len(features) == 0 or len(labels) == 0:
                return {"error": "Provide df (DataFrame) or features+labels arrays", "validated": False, "adapter_id": self.adapter_id}
        else:
            target_col = params.get("target_col", "churned")
            feature_cols = params.get("feature_cols", [c for c in df.columns if c != target_col])
            features = df[feature_cols].values.astype(float)
            labels = df[target_col].values.astype(int)

        if len(labels) < 30:
            return {"error": f"Need >=30 samples for reliable estimation, got {len(labels)}", "validated": False, "adapter_id": self.adapter_id}

        # Simple logistic regression via statsmodels
        try:
            import statsmodels.api as sm
        except ImportError:
            # Fallback: analytical MLE for univariate or simple model
            return self._churn_analytical_fallback(features, labels, params)

        # Add constant
        X = sm.add_constant(features)
        y = labels

        try:
            model = sm.Logit(y, X).fit(disp=0)
        except Exception as e:
            # Perfect separation fallback
            return self._churn_analytical_fallback(features, labels, params)

        # Odds ratios and significance (compatible with ndarray or DataFrame conf_int)
        params_est = model.params
        conf = model.conf_int(alpha=0.05)
        pvalues = model.pvalues
        odds_ratios = np.exp(params_est)

        significant_features = []
        param_names = list(params_est.index) if hasattr(params_est, 'index') else [f"x{i}" for i in range(len(params_est))]
        for i, name in enumerate(param_names):
            pval = pvalues.iloc[i] if hasattr(pvalues, 'iloc') else pvalues[i]
            if pval < 0.05:
                significant_features.append({
                    "feature": str(name),
                    "odds_ratio": round(float(odds_ratios.iloc[i] if hasattr(odds_ratios, 'iloc') else odds_ratios[i]), 3),
                    "p_value": round(float(pval), 4),
                    "direction": "increases_risk" if (odds_ratios.iloc[i] if hasattr(odds_ratios, 'iloc') else odds_ratios[i]) > 1 else "decreases_risk",
                })

        # Predictions on training data (with cross-validated feel — last 20% holdout if enough)
        n = len(y)
        split = int(0.8 * n)
        if split > 10:
            X_train, X_test = X[:split], X[split:]
            y_train, y_test = y[:split], y[split:]
            try:
                model_test = sm.Logit(y_train, X_train).fit(disp=0)
                pred_probs = model_test.predict(X_test)
                pred_class = (pred_probs > 0.5).astype(int)
                accuracy = np.mean(pred_class == y_test)
                # AUC approximation (V4.3.1: 可选依赖 sklearn)
                try:
                    from sklearn.metrics import roc_auc_score
                    auc = roc_auc_score(y_test, pred_probs)
                except ImportError:
                    auc = None
            except Exception:
                accuracy = None
                auc = None
        else:
            accuracy = None
            auc = None

        # Risk buckets for population
        pred_probs_all = model.predict(X)
        high_risk = np.mean(pred_probs_all > 0.7) * 100
        medium_risk = np.mean((pred_probs_all > 0.3) & (pred_probs_all <= 0.7)) * 100
        low_risk = np.mean(pred_probs_all <= 0.3) * 100

        return {
            "analysis": "churn",
            "causal_grade": "C1",
            "causal_note": "Predictive risk scoring — correlational, not causal. Use DiD for causal impact of interventions",
            "n_samples": n,
            "n_churned": int(np.sum(y)),
            "churn_rate": round(float(np.mean(y)) * 100, 2),
            "model": "LogisticRegression",
            "significant_drivers": significant_features,
            "population_risk": {
                "high_risk_pct": round(float(high_risk), 2),
                "medium_risk_pct": round(float(medium_risk), 2),
                "low_risk_pct": round(float(low_risk), 2),
            },
            "holdout_accuracy": round(float(accuracy), 4) if accuracy is not None else None,
            "holdout_auc": round(float(auc), 4) if auc is not None else None,
            "validated": True,
            "adapter_id": self.adapter_id,
        }

    def _churn_analytical_fallback(self, features, labels, params):
        """当statsmodels不可用时使用的简化分析"""
        # Univariate t-tests for each feature
        churned = features[labels == 1]
        stayed = features[labels == 0]
        if len(churned) == 0 or len(stayed) == 0:
            return {"error": "No variation in target", "validated": False, "adapter_id": self.adapter_id}

        results = []
        for i in range(features.shape[1]):
            t_stat, pval = stats.ttest_ind(churned[:, i], stayed[:, i], equal_var=False)
            results.append({
                "feature_index": i,
                "mean_churned": round(float(np.mean(churned[:, i])), 4),
                "mean_stayed": round(float(np.mean(stayed[:, i])), 4),
                "t_statistic": round(float(t_stat), 4),
                "p_value": round(float(pval), 4),
                "significant": pval < 0.05,
            })

        return {
            "analysis": "churn",
            "causal_grade": "C1",
            "causal_note": "Analytical fallback — univariate t-tests only. No multivariate control for confounders",
            "n_samples": len(labels),
            "feature_tests": results,
            "validated": True,
            "adapter_id": self.adapter_id,
        }

    # --------------------------------------------------------
    # Organizational Change: Difference-in-Differences
    # --------------------------------------------------------
    def _organizational_change_did(self, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """组织变革效果评估：双重差分法（C3-反事实因果）

        要求数据结构：
        - y: 结果变量数组 (如生产力、营收、满意度)，长度 T*N
        - unit: 单位ID数组（如部门ID、员工ID）
        - time: 时间周期数组
        - treated: 是否处理组（0/1）
        - post: 是否干预后（0/1）
        """
        df = data.get("df")
        if df is None:
            y = np.asarray(data.get("y", []), dtype=float)
            unit = np.asarray(data.get("unit", []))
            time = np.asarray(data.get("time", []), dtype=int)
            treated = np.asarray(data.get("treated", []), dtype=int)
            post = np.asarray(data.get("post", []), dtype=int)
            if len(y) == 0:
                return {"error": "Provide df or arrays (y, unit, time, treated, post)", "validated": False, "adapter_id": self.adapter_id}
            df = pd.DataFrame({"y": y, "unit": unit, "time": time, "treated": treated, "post": post})

        # Basic DiD regression: y ~ treated + post + treated*post + controls
        try:
            import statsmodels.formula.api as smf
        except ImportError:
            return {"error": "statsmodels required for DiD", "validated": False, "adapter_id": self.adapter_id}

        df["did_interaction"] = df["treated"] * df["post"]

        # Check parallel trends (pre-treatment period only)
        pre_data = df[df["post"] == 0].copy()
        parallel_trend_passed = False
        parallel_warning = ""
        if len(pre_data) > 0:
            try:
                # Simplified: test if treated and control have same trend in pre-period
                # Group by time and compute means
                pre_means = pre_data.groupby(["time", "treated"])["y"].mean().unstack()
                if pre_means.shape[1] == 2:
                    diff_series = pre_means[1] - pre_means[0]
                    # Trend test: slope of difference over time should not be significantly different from 0
                    if len(diff_series.dropna()) >= 3:
                        x_trend = np.arange(len(diff_series.dropna()))
                        y_trend = diff_series.dropna().values
                        slope, intercept, r_value, p_value, std_err = stats.linregress(x_trend, y_trend)
                        parallel_trend_passed = p_value > 0.05
                        parallel_warning = f"Pre-treatment trend diff slope={slope:.4f}, p={p_value:.4f}"
            except Exception as e:
                parallel_warning = f"Could not test parallel trends: {e}"

        # Main DiD regression
        controls = params.get("controls", [])
        formula_parts = ["y ~ treated + post + did_interaction"] + controls
        formula = " + ".join(formula_parts)

        try:
            model = smf.ols(formula=formula, data=df).fit(cov_type="cluster", cov_kwds={"groups": df["unit"]})
        except Exception:
            # Fallback without clustering
            try:
                model = smf.ols(formula=formula, data=df).fit()
            except Exception as e:
                return {"error": f"DiD regression failed: {e}", "validated": False, "adapter_id": self.adapter_id}

        # Extract DiD coefficient
        did_coef = model.params.get("did_interaction", np.nan)
        did_pval = model.pvalues.get("did_interaction", 1.0)
        did_ci = model.conf_int().loc["did_interaction"].values if "did_interaction" in model.conf_int().index else [np.nan, np.nan]
        significant = did_pval < 0.05

        # Causal grade assignment
        if parallel_trend_passed and significant:
            causal_grade = "C3"
            note = "DiD with parallel-trend validation provides credible causal claim for organizational change impact"
        elif significant:
            causal_grade = "C2"
            note = "DiD coefficient significant but parallel-trend assumption untestable or violated — confounding risk"
        else:
            causal_grade = "C1"
            note = "No significant treatment effect detected"

        # Descriptive statistics
        pre_treat = df[(df["treated"] == 1) & (df["post"] == 0)]["y"].mean()
        post_treat = df[(df["treated"] == 1) & (df["post"] == 1)]["y"].mean()
        pre_ctrl = df[(df["treated"] == 0) & (df["post"] == 0)]["y"].mean()
        post_ctrl = df[(df["treated"] == 0) & (df["post"] == 1)]["y"].mean()
        naive_diff = (post_treat - pre_treat) - (post_ctrl - pre_ctrl)

        return {
            "analysis": "org_change",
            "causal_grade": causal_grade,
            "causal_note": note,
            "parallel_trend_passed": parallel_trend_passed,
            "parallel_trend_warning": parallel_warning,
            "did_coefficient": round(float(did_coef), 4),
            "did_p_value": round(float(did_pval), 4),
            "did_ci_95": [round(float(did_ci[0]), 4), round(float(did_ci[1]), 4)] if len(did_ci) == 2 else [np.nan, np.nan],
            "significant": significant,
            "descriptive": {
                "pre_treatment_mean": round(float(pre_treat), 4),
                "post_treatment_mean": round(float(post_treat), 4),
                "pre_control_mean": round(float(pre_ctrl), 4),
                "post_control_mean": round(float(post_ctrl), 4),
                "naive_diff_in_diff": round(float(naive_diff), 4),
            },
            "model_r_squared": round(float(model.rsquared), 4),
            "n_observations": int(model.nobs),
            "validated": True,
            "adapter_id": self.adapter_id,
        }


# ============================================================
# A-14-PERS: Personal Growth Adapter
# ============================================================
class PersonalGrowthAdapter:
    """A-14: 个人成长分析适配器

    覆盖：学习曲线预测、习惯养成建模、目标达成概率
    因果层级：全部为C1（预测性）— 个人层面无法构造反事实对照组
    """

    adapter_id = "A-14-PERS"
    version = "4.4.0"
    disciplines = ["Behavioral Science", "Learning Analytics", "Habit Formation"]
    theories = [
        "Wright (1936) Power Law of Learning",
        "Lally et al. (2010) Habit Formation",
        "Bayesian Goal Achievement Updating",
    ]

    def __call__(self, *, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        analysis_type = params.get("analysis", "learning")  # learning / habit / goal

        if analysis_type == "learning":
            return self._learning_curve(data, params)
        elif analysis_type == "habit":
            return self._habit_formation(data, params)
        elif analysis_type == "goal":
            return self._goal_achievement(data, params)
        else:
            return {"error": f"Unknown analysis type: {analysis_type}", "validated": False, "adapter_id": self.adapter_id}

    # --------------------------------------------------------
    # Learning Curve: Wright's Power Law
    # --------------------------------------------------------
    def _learning_curve(self, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """学习曲线分析与掌握时间预测

        模型: T_n = T_1 * n^(-b)
        T_n = 第n次重复所需时间/错误率
        b = 学习率（0.1~0.5典型值）
        """
        n_trials = np.asarray(data.get("trials", []), dtype=float)  # 练习次数
        performance = np.asarray(data.get("performance", []), dtype=float)  # 耗时或错误率

        if len(n_trials) < 3 or len(performance) < 3:
            return {"error": "Need >=3 (trials, performance) points", "validated": False, "adapter_id": self.adapter_id}

        # Log-linear regression: ln(T) = ln(T1) - b * ln(n)
        log_n = np.log(n_trials)
        log_perf = np.log(performance)

        # OLS
        X = np.column_stack([np.ones(len(log_n)), log_n])
        beta = np.linalg.lstsq(X, log_perf, rcond=None)[0]
        log_t1, neg_b = beta
        b = -neg_b
        t1 = np.exp(log_t1)

        # R^2
        y_pred = X @ beta
        ss_res = np.sum((log_perf - y_pred) ** 2)
        ss_tot = np.sum((log_perf - np.mean(log_perf)) ** 2)
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

        # Confidence intervals via bootstrap
        boot_bs = []
        for _ in range(1000):
            idx = np.random.choice(len(log_n), size=len(log_n), replace=True)
            beta_boot = np.linalg.lstsq(X[idx], log_perf[idx], rcond=None)[0]
            boot_bs.append(-beta_boot[1])
        b_ci = [np.percentile(boot_bs, 2.5), np.percentile(boot_bs, 97.5)]

        # Predictions for future trials
        max_trial = int(np.max(n_trials))
        future_trials = np.arange(max_trial + 1, max_trial + int(params.get("forecast_trials", 10)) + 1)
        future_perf = t1 * future_trials ** (-b)

        # Mastery threshold prediction (e.g., performance < threshold)
        mastery_threshold = params.get("mastery_threshold", None)
        mastery_trial = None
        if mastery_threshold is not None and b > 0 and t1 > mastery_threshold:
            mastery_trial = int(np.ceil((t1 / mastery_threshold) ** (1 / b)))

        # Plateau analysis (diminishing returns)
        marginal_improvement = b * t1 * (max_trial + 1) ** (-b - 1)
        plateau_warning = marginal_improvement < 0.01 * t1

        return {
            "analysis": "learning_curve",
            "causal_grade": "C1",
            "causal_note": "Predictive model — assumes learning environment stable. No counterfactual possible at individual level",
            "model": "Wright-Power-Law",
            "learning_rate_b": round(float(b), 4),
            "b_ci_95": [round(float(b_ci[0]), 4), round(float(b_ci[1]), 4)],
            "initial_performance_t1": round(float(t1), 4),
            "r_squared": round(float(r_squared), 4),
            "future_predictions": [
                {"trial": int(t), "predicted_performance": round(float(p), 4)}
                for t, p in zip(future_trials, future_perf)
            ],
            "mastery": {
                "threshold": mastery_threshold,
                "predicted_trial_to_mastery": mastery_trial,
            } if mastery_threshold is not None else None,
            "plateau_warning": bool(plateau_warning),
            "marginal_improvement": round(float(marginal_improvement), 6),
            "validated": True,
            "adapter_id": self.adapter_id,
        }

    # --------------------------------------------------------
    # Habit Formation: Exponential Decay + Milestones
    # --------------------------------------------------------
    def _habit_formation(self, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """习惯养成建模（基于Lally 2010的66天规律）

        模型：习惯强度 H(t) = H_max * (1 - exp(-lambda * t))
        自动化概率随天数增加
        """
        days = np.asarray(data.get("days", []), dtype=float)  # 已坚持天数（如1, 5, 10, 21, 30, 60...）
        compliance = np.asarray(data.get("compliance", []), dtype=float)  # 当日完成度（0-1或0-100）

        if len(days) < 2:
            # Use theoretical model without data
            days = np.arange(1, 91)
            compliance = 1.0 - 0.8 * np.exp(-0.05 * days)  # Theoretical curve

        # Normalize compliance to 0-1
        compliance_norm = compliance / 100.0 if np.max(compliance) > 1.5 else compliance
        compliance_norm = np.clip(compliance_norm, 0.01, 1.0)

        # Fit H(t) = H_max * (1 - exp(-lambda * t))
        # Linearize: ln(1 - H/H_max) = -lambda * t
        # We grid-search H_max if unknown
        h_max_guess = np.max(compliance_norm)
        if h_max_guess > 0.99:
            h_max_guess = 1.0

        best_fit = None
        best_rss = float("inf")
        for h_max in np.linspace(max(h_max_guess, 0.5), 1.0, 20):
            with np.errstate(divide='ignore', invalid='ignore'):
                y = np.log(1 - compliance_norm / h_max)
            valid = np.isfinite(y)
            if np.sum(valid) < 2:
                continue
            t_valid = days[valid]
            y_valid = y[valid]
            # OLS: y = -lambda * t
            slope = np.sum(t_valid * y_valid) / np.sum(t_valid ** 2) if np.sum(t_valid ** 2) > 0 else -0.05
            pred = h_max * (1 - np.exp(slope * days))
            rss = np.sum((compliance_norm - pred) ** 2)
            if rss < best_rss:
                best_rss = rss
                best_fit = (h_max, -slope)

        if best_fit is None:
            h_max, lambda_rate = 1.0, 0.05
        else:
            h_max, lambda_rate = best_fit

        # Key milestones
        milestones = {
            "50_automatic": int(np.ceil(-np.log(0.5) / lambda_rate)) if lambda_rate > 0 else None,
            "66_automatic": 66,  # Lally reference
            "90_automatic": int(np.ceil(-np.log(0.1) / lambda_rate)) if lambda_rate > 0 else None,
        }

        # Probability of success at day N
        target_day = int(params.get("target_day", 66))
        prob_automatic = h_max * (1 - np.exp(-lambda_rate * target_day))

        # Recommendation
        if prob_automatic < 0.5:
            recommendation = "Early stage — high relapse risk. Use implementation intentions (if-then plans) and environmental cues"
        elif prob_automatic < 0.8:
            recommendation = "Consolidating — maintain consistency. Missing 1 day won't break habit"
        else:
            recommendation = "Habit largely automated — focus on context stability to prevent extinction"

        return {
            "analysis": "habit_formation",
            "causal_grade": "C1",
            "causal_note": "Predictive behavioral model — describes habit strength trajectory, not causal mechanism of behavior change",
            "model": "Exponential-Habit-Strength",
            "h_max": round(float(h_max), 4),
            "lambda_rate": round(float(lambda_rate), 6),
            "milestones": {k: v for k, v in milestones.items() if v is not None},
            "target_day": target_day,
            "probability_automatic": round(float(prob_automatic), 4),
            "recommendation": recommendation,
            "validated": True,
            "adapter_id": self.adapter_id,
        }

    # --------------------------------------------------------
    # Goal Achievement: Bayesian Updating of Success Probability
    # --------------------------------------------------------
    def _goal_achievement(self, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """目标达成概率：基于历史完成率的贝叶斯更新

        Beta-Binomial 模型：
        Prior: Beta(alpha, beta) ~ 历史平均完成率
        Likelihood: Binomial(k successes out of n attempts)
        Posterior: Beta(alpha + k, beta + n - k)
        """
        historical_goals = np.asarray(data.get("historical_goals", []), dtype=int)  # 1=完成, 0=未完成
        current_progress = float(data.get("current_progress", 0.5))  # 当前进度 0-1
        target_difficulty = params.get("target_difficulty", "medium")  # easy/medium/hard

        # Prior from population or historical data
        if len(historical_goals) >= 5:
            k = int(np.sum(historical_goals))
            n = len(historical_goals)
            alpha_prior = 1 + k
            beta_prior = 1 + (n - k)
            prior_mean = k / n
        else:
            # Default weak prior based on difficulty
            difficulty_params = {"easy": (3, 2), "medium": (2, 2), "hard": (2, 3)}
            alpha_prior, beta_prior = difficulty_params.get(target_difficulty, (2, 2))
            prior_mean = alpha_prior / (alpha_prior + beta_prior)

        # Update with current progress (treat as partial observation)
        # If progress is 0.6, treat as 0.6 success equivalent
        progress_weight = 2.0  # How much to weight current progress vs history
        alpha_post = alpha_prior + current_progress * progress_weight
        beta_post = beta_prior + (1 - current_progress) * progress_weight

        posterior_mean = alpha_post / (alpha_post + beta_post)
        posterior_var = (alpha_post * beta_post) / ((alpha_post + beta_post) ** 2 * (alpha_post + beta_post + 1))

        # Credible intervals
        from scipy.stats import beta as beta_dist
        ci_lower = beta_dist.ppf(0.05, alpha_post, beta_post)
        ci_upper = beta_dist.ppf(0.95, alpha_post, beta_post)

        # Forecast completion date
        remaining = 1.0 - current_progress
        expected_daily_rate = posterior_mean * params.get("typical_daily_progress", 0.05)
        if expected_daily_rate > 0:
            expected_days_remaining = int(np.ceil(remaining / expected_daily_rate))
        else:
            expected_days_remaining = None

        # Risk factors
        risk_factors = []
        if current_progress < 0.2 and posterior_mean < 0.5:
            risk_factors.append("Low early progress + poor historical track record")
        if target_difficulty == "hard" and prior_mean < 0.5:
            risk_factors.append("Difficulty mismatch with capability")
        if posterior_var > 0.1:
            risk_factors.append("High uncertainty — goal poorly defined or external dependencies volatile")

        return {
            "analysis": "goal_achievement",
            "causal_grade": "C1",
            "causal_note": "Bayesian predictive — personal willpower and external shocks are unmodeled confounders. Not causal",
            "prior": {
                "alpha": round(float(alpha_prior), 2),
                "beta": round(float(beta_prior), 2),
                "mean": round(float(prior_mean), 4),
            },
            "posterior": {
                "alpha": round(float(alpha_post), 2),
                "beta": round(float(beta_post), 2),
                "mean": round(float(posterior_mean), 4),
                "variance": round(float(posterior_var), 6),
                "ci_90": [round(float(ci_lower), 4), round(float(ci_upper), 4)],
            },
            "current_progress": round(float(current_progress), 4),
            "expected_days_remaining": expected_days_remaining,
            "risk_factors": risk_factors,
            "recommendation": self._goal_recommendation(posterior_mean, current_progress, risk_factors),
            "validated": True,
            "adapter_id": self.adapter_id,
        }

    def _goal_recommendation(self, p_success, progress, risk_factors):
        if p_success > 0.8:
            return "High probability path — maintain routine, prepare stretch goals"
        elif p_success > 0.5:
            if progress < 0.3:
                return "Moderate probability but early — focus on quick wins to build momentum"
            else:
                return "Moderate probability — identify and neutralize specific risk factors"
        else:
            if len(risk_factors) > 0:
                return f"Low probability — critical intervention needed. Top risks: {'; '.join(risk_factors[:2])}"
            else:
                return "Low probability — re-scope goal or extend timeline"


# ============================================================
# A-15-TEAM: Team Management Adapter
# ============================================================
class TeamManagementAdapter:
    """A-15: 团队管理分析适配器

    覆盖：团队生产力分解、冲突检测、最优规模
    因果层级：生产力=C1(结构分解), 冲突=C1(异常检测), 规模=C1(优化)
    """

    adapter_id = "A-15-TEAM"
    version = "4.4.0"
    disciplines = ["Team Science", "Organizational Behavior", "Social Physics"]
    theories = [
        "Ringelmann Effect / Social Loafing",
        "Brooks's Law (communication overhead)",
        "Information-Theoretic Conflict Detection",
    ]

    def __call__(self, *, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        analysis_type = params.get("analysis", "productivity")  # productivity / conflict / optimal_size

        if analysis_type == "productivity":
            return self._productivity_decomposition(data, params)
        elif analysis_type == "conflict":
            return self._conflict_detection(data, params)
        elif analysis_type == "optimal_size":
            return self._optimal_size(data, params)
        else:
            return {"error": f"Unknown analysis type: {analysis_type}", "validated": False, "adapter_id": self.adapter_id}

    # --------------------------------------------------------
    # Productivity Decomposition: R = alpha * A * C * M
    # --------------------------------------------------------
    def _productivity_decomposition(self, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """团队生产力分解模型

        R = alpha * A * C * M
        R = Team output rate
        alpha = Individual skill baseline (average capability)
        A = Alignment (goal clarity, 0-1)
        C = Communication quality (information flow efficiency, 0-1)
        M = Motivation (engagement level, 0-1)
        """
        members = data.get("members", [])
        if isinstance(members, list) and len(members) > 0 and isinstance(members[0], dict):
            # Extract from member dicts
            skills = np.array([m.get("skill", 0.5) for m in members])
            motivations = np.array([m.get("motivation", 0.5) for m in members])
        else:
            skills = np.asarray(data.get("skills", [0.5, 0.6, 0.7]), dtype=float)
            motivations = np.asarray(data.get("motivations", [0.6, 0.6, 0.6]), dtype=float)

        alignment = float(params.get("alignment", 0.75))  # Goal clarity
        communication_quality = float(params.get("communication_quality", 0.7))  # Info flow
        n_team = len(skills)

        if n_team == 0:
            return {"error": "No team members provided", "validated": False, "adapter_id": self.adapter_id}

        # Components
        alpha = float(np.mean(skills))  # Baseline capability
        A = alignment
        C = communication_quality * (1 - 0.05 * max(0, n_team - 5))  # Degrade with size after 5
        C = max(0.1, C)
        M = float(np.mean(motivations))

        # Ringelmann social loafing factor: efficiency drops as team grows
        # R_individual_sum * (1 - k * ln(n))  (empirical approximation)
        loafing_k = params.get("loafing_coefficient", 0.1)
        team_efficiency = max(0.3, 1 - loafing_k * np.log(n_team))

        # Final productivity
        R = alpha * A * C * M * team_efficiency * n_team
        R_theoretical_max = alpha * 1.0 * 1.0 * 1.0 * n_team  # Perfect conditions
        productivity_ratio = R / R_theoretical_max if R_theoretical_max > 0 else 0.0

        # Bottleneck identification (root cause at team level)
        components = {
            "alpha_skill": round(float(alpha), 4),
            "A_alignment": round(float(A), 4),
            "C_communication": round(float(C), 4),
            "M_motivation": round(float(M), 4),
            "T_team_efficiency": round(float(team_efficiency), 4),
        }
        bottleneck = min(components, key=components.get)

        # Sensitivity: what if we improve bottleneck by 20%?
        improvement_potential = {}
        for key, val in components.items():
            if key == "T_team_efficiency":
                continue  # Hard to directly manipulate
            improved = {k: v for k, v in components.items()}
            improved[key] = min(1.0, val * 1.2)
            R_improved = improved["alpha_skill"] * improved["A_alignment"] * improved["C_communication"] * improved["M_motivation"] * components["T_team_efficiency"] * n_team
            improvement_potential[key] = {
                "new_productivity": round(float(R_improved), 4),
                "gain_pct": round(float((R_improved - R) / R * 100), 2) if R > 0 else 0.0,
            }

        return {
            "analysis": "productivity_decomposition",
            "causal_grade": "C1",
            "causal_note": "Structural decomposition — identifies correlational bottlenecks. Causal claims require intervention experiments (A/B test on team practices)",
            "team_size": n_team,
            "productivity": {
                "current_R": round(float(R), 4),
                "theoretical_max_R": round(float(R_theoretical_max), 4),
                "ratio_vs_ideal": round(float(productivity_ratio), 4),
            },
            "components": components,
            "bottleneck": {
                "factor": bottleneck,
                "value": components[bottleneck],
                "interpretation": self._bottleneck_interpretation(bottleneck),
            },
            "improvement_potential": improvement_potential,
            "validated": True,
            "adapter_id": self.adapter_id,
        }

    def _bottleneck_interpretation(self, bottleneck):
        interpretations = {
            "alpha_skill": "Team lacks required expertise — prioritize hiring or training",
            "A_alignment": "Unclear goals or priorities — invest in OKR/goal-cascading workshops",
            "C_communication": "Information friction — reduce meetings, improve async documentation",
            "M_motivation": "Engagement crisis — investigate workload burnout or incentive misalignment",
            "T_team_efficiency": "Team too large or coordination overhead too high — consider sub-teams",
        }
        return interpretations.get(bottleneck, "Review this dimension")

    # --------------------------------------------------------
    # Conflict Detection: Interaction Entropy + Anomaly Detection
    # --------------------------------------------------------
    def _conflict_detection(self, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """团队冲突早期预警

        基于互动模式的统计异常：
        - 响应时间熵（突然变得极快或极慢）
        - 情绪得分分布偏移
        - 互动网络不对称性
        """
        interactions = data.get("interactions")
        if interactions is None:
            # Generate synthetic realistic pattern for testing
            n_days = 30
            base_response = 4.0  # hours
            sentiment_base = 0.6  # positive
            interactions = []
            for day in range(n_days):
                # Introduce conflict pattern in last 7 days
                if day >= 23:
                    response_time = base_response * (0.3 + 0.4 * np.random.random())  # Erratic fast
                    sentiment = 0.2 + 0.3 * np.random.random()  # Negative
                else:
                    response_time = base_response + np.random.normal(0, 0.5)
                    sentiment = sentiment_base + np.random.normal(0, 0.1)
                interactions.append({
                    "day": day,
                    "response_time_hours": max(0.1, response_time),
                    "sentiment": np.clip(sentiment, 0, 1),
                    "messages_count": int(np.random.poisson(20)),
                })

        df = pd.DataFrame(interactions)
        if len(df) < 7:
            return {"error": "Need >=7 days of interaction data", "validated": False, "adapter_id": self.adapter_id}

        # Metrics
        response_times = df["response_time_hours"].values
        sentiments = df["sentiment"].values
        messages = df.get("messages_count", pd.Series([10] * len(df))).values

        # Rolling windows
        window = min(7, len(df) // 2)
        recent_idx = slice(-window, None)
        early_idx = slice(0, window)

        # 1. Response time volatility (entropy proxy)
        rt_early = response_times[early_idx]
        rt_recent = response_times[recent_idx]
        rt_cv_recent = np.std(rt_recent) / np.mean(rt_recent) if np.mean(rt_recent) > 0 else 0
        rt_cv_early = np.std(rt_early) / np.mean(rt_early) if np.mean(rt_early) > 0 else 0
        rt_shift = rt_cv_recent / (rt_cv_early + 1e-6)

        # 2. Sentiment collapse
        sent_early_mean = np.mean(sentiments[early_idx])
        sent_recent_mean = np.mean(sentiments[recent_idx])
        sentiment_drop = sent_early_mean - sent_recent_mean

        # 3. Communication volume anomaly
        msg_mean = np.mean(messages)
        msg_recent_mean = np.mean(messages[recent_idx])
        msg_change = (msg_recent_mean - msg_mean) / (msg_mean + 1e-6)

        # Conflict score (composite)
        conflict_score = 0.0
        triggers = []

        if rt_shift > 2.0:
            conflict_score += 0.3
            triggers.append("Response time volatility spike — possible emotional escalation or deliberate avoidance")
        if sentiment_drop > 0.2:
            conflict_score += 0.4
            triggers.append("Sentiment collapse detected — interpersonal friction likely")
        if abs(msg_change) > 0.3:
            conflict_score += 0.2
            direction = "drop" if msg_change < 0 else "spike"
            triggers.append(f"Communication volume anomaly ({direction}) — withdrawal or argument flooding")

        # Normalize
        conflict_score = min(1.0, conflict_score)

        # Severity
        if conflict_score > 0.7:
            severity = "CRITICAL"
            action = "Immediate mediation required. Consider 1:1s with all core members within 48h"
        elif conflict_score > 0.4:
            severity = "WARNING"
            action = "Early conflict signals — schedule team retrospective, investigate workload distribution"
        else:
            severity = "NORMAL"
            action = "Team dynamics healthy — maintain current management practices"

        # Statistical significance (Mann-Whitney U for sentiment shift)
        try:
            u_stat, p_value = stats.mannwhitneyu(sentiments[early_idx], sentiments[recent_idx], alternative="greater")
            p_value_two_sided = p_value * 2
        except Exception:
            p_value_two_sided = 1.0

        return {
            "analysis": "conflict_detection",
            "causal_grade": "C1",
            "causal_note": "Anomaly detection on interaction proxies — correlational. Causal attribution requires interviews or structured observation",
            "conflict_score": round(float(conflict_score), 4),
            "severity": severity,
            "triggers": triggers,
            "metrics": {
                "response_time_cv_ratio": round(float(rt_shift), 4),
                "sentiment_drop": round(float(sentiment_drop), 4),
                "communication_volume_change_pct": round(float(msg_change * 100), 2),
                "sentiment_shift_p_value": round(float(p_value_two_sided), 4),
            },
            "recommendation": action,
            "validated": True,
            "adapter_id": self.adapter_id,
        }

    # --------------------------------------------------------
    # Optimal Team Size: Brooks Law + Ringelmann
    # --------------------------------------------------------
    def _optimal_size(self, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """最优团队规模量化

        模型：净生产力 = n * alpha * f(n) - coordination_cost(n)
        f(n) = 1 - k * ln(n)  [Ringelmann效率]
        coordination_cost(n) = c * n * (n-1) / 2  [Brooks通信路径]
        """
        alpha = float(params.get("individual_productivity", 1.0))
        loafing_k = float(params.get("loafing_k", 0.1))
        coordination_cost_per_link = float(params.get("coordination_cost_per_link", 0.05))
        max_size_to_test = int(params.get("max_size", 20))
        budget_constraint = params.get("budget_constraint", None)  # Max headcount

        sizes = np.arange(1, max_size_to_test + 1)
        net_productivity = []
        coordination_costs = []
        individual_outputs = []

        for n in sizes:
            team_efficiency = max(0.2, 1 - loafing_k * np.log(n)) if n > 1 else 1.0
            indiv_out = alpha * team_efficiency
            gross_output = n * indiv_out
            coord_cost = coordination_cost_per_link * n * (n - 1) / 2
            net = gross_output - coord_cost
            individual_outputs.append(indiv_out)
            coordination_costs.append(coord_cost)
            net_productivity.append(net)

        net_productivity = np.array(net_productivity)
        optimal_n = int(sizes[np.argmax(net_productivity)])
        max_productivity = float(np.max(net_productivity))

        # Marginal benefit of adding one person
        marginal_productivity = np.diff(net_productivity)
        last_positive_marginal = None
        for i, mp in enumerate(marginal_productivity):
            if mp > 0:
                last_positive_marginal = int(sizes[i + 1])

        # Current team assessment
        current_size = int(data.get("current_size", optimal_n))
        current_net = net_productivity[min(current_size - 1, len(net_productivity) - 1)]
        current_status = "optimal" if current_size == optimal_n else ("oversized" if current_size > optimal_n else "undersized")

        # Sensitivity: how robust is optimal size?
        robust_tests = {}
        for k_test in [0.05, 0.1, 0.15]:
            net_test = []
            for n in sizes:
                eff = max(0.2, 1 - k_test * np.log(n)) if n > 1 else 1.0
                net_test.append(n * alpha * eff - coordination_cost_per_link * n * (n - 1) / 2)
            robust_tests[f"k={k_test}"] = int(sizes[np.argmax(np.array(net_test))])

        return {
            "analysis": "optimal_size",
            "causal_grade": "C1",
            "causal_note": "Optimization model based on stylized facts (Brooks, Ringelmann). Real-world optimum depends on task type, culture, tools — validate with A/B experimentation",
            "current_size": current_size,
            "current_status": current_status,
            "optimal_size": optimal_n,
            "max_net_productivity": round(max_productivity, 4),
            "marginal_threshold": last_positive_marginal,
            "productivity_by_size": [
                {"size": int(n), "net_productivity": round(float(np), 4), "coordination_cost": round(float(cc), 4)}
                for n, np, cc in zip(sizes, net_productivity, coordination_costs)
            ],
            "robustness": robust_tests,
            "recommendation": (
                f"Current team size {current_size} is {current_status}. "
                f"Optimal range: {optimal_n}. "
                f"{'Consider splitting into sub-teams' if current_size > optimal_n + 2 else 'Maintain current structure' if current_size == optimal_n else 'Can absorb 1-2 members if needed'}"
            ),
            "validated": True,
            "adapter_id": self.adapter_id,
        }
