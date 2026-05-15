"""
statistical_rigor.py — V4.2.0-GA 统计严谨性层
==============================================
块Bootstrap (Moving Block Bootstrap) + FDR多重检验校正

设计原则（V4.2.0-GA）:
  · 增量增强 — 不修改现有管线文件，仅被端到端对比管道引用
  · 向后兼容 — 所有函数具有独立可用性，无全局副作用
  · 无缝接入 — 函数签名与现有CUSUM/Granger调用约定一致

约束条款（V4.2.0-GA强制）:
  C1: 时间序列Bootstrap必须使用块Bootstrap (b = floor(T^(1/3)))
  C2: CUSUM相变点必须经BH-FDR校正 (α=0.05) 方可认定为"显著"
  C3: 报告格式为 "N个候选 / M个FDR显著"

参考文献:
  Lahiri (2003) Resampling Methods for Dependent Data — 块Bootstrap最优块长理论
  Benjamini & Hochberg (1995) Controlling the FDR — BH过程
  Brown, Durbin & Evans (1975) — CUSUM检验
"""

import numpy as np
from typing import List, Tuple, Optional, Callable, Dict, Any


# ═══════════════════════════════════════════════════════════════
# 1. 块Bootstrap引擎
# ═══════════════════════════════════════════════════════════════

def block_bootstrap(
    data: np.ndarray,
    block_len: Optional[int] = None,
    n_boot: int = 1000,
    statistic_fn: Optional[Callable] = None,
    alpha: float = 0.05,
    seed: int = 42,
) -> Dict[str, Any]:
    """Moving Block Bootstrap (MBB) — 时间序列专用重采样

    算法: Lahiri (2003) Moving Block Bootstrap
    - 将序列切分为长度为b的重叠块
    - 每次有放回抽取k = ceil(T/b)个块，拼接截断至原长T
    - 保留了块内的时间依赖结构

    Args:
        data: 一维时间序列 (T,)
        block_len: 块长度, 默认 floor(T^(1/3)), 最小2
        n_boot: Bootstrap重采样次数
        statistic_fn: 统计量函数 f(data) -> scalar, 默认np.mean
        alpha: 置信水平 (双侧)
        seed: 随机种子

    Returns:
        dict: {
            'estimates':  (n_boot,) Bootstrap统计量分布,
            'ci_lower':   百分位CI下界,
            'ci_upper':   百分位CI上界,
            'block_len':  实际使用的块长,
            'n_blocks':   每轮抽取的块数,
            'obs_stat':   原始数据上的统计量值,
        }
    """
    rng = np.random.default_rng(seed)
    T = len(data)

    if block_len is None:
        block_len = max(2, int(np.round(T ** (1 / 3))))
    block_len = min(block_len, T)  # 不能超过T
    n_blocks = max(1, int(np.ceil(T / block_len)))

    if statistic_fn is None:
        statistic_fn = np.mean

    obs_stat = float(statistic_fn(data))
    estimates = np.zeros(n_boot)

    # 预计算所有可能块 (重叠滑窗)
    n_possible = T - block_len + 1
    blocks = np.array([data[i:i + block_len] for i in range(n_possible)])

    for b in range(n_boot):
        # 有放回抽取 n_blocks 个块
        idx = rng.integers(0, n_possible, size=n_blocks)
        boot_series = np.concatenate(blocks[idx])[:T]  # 截断至T
        estimates[b] = float(statistic_fn(boot_series))

    ci_lower = float(np.percentile(estimates, 100 * alpha / 2))
    ci_upper = float(np.percentile(estimates, 100 * (1 - alpha / 2)))

    return {
        'estimates': estimates,
        'ci_lower': ci_lower,
        'ci_upper': ci_upper,
        'block_len': block_len,
        'n_blocks': n_blocks,
        'obs_stat': obs_stat,
    }


# ═══════════════════════════════════════════════════════════════
# 2. CUSUM相变点的块Bootstrap p值
# ═══════════════════════════════════════════════════════════════

def cusum_block_bootstrap_pvalues(
    data: np.ndarray,
    change_indices: List[int],
    n_boot: int = 1000,
    block_len: Optional[int] = None,
    window_factor: int = 5,
    seed: int = 42,
) -> List[float]:
    """为每个CUSUM检测点生成块Bootstrap p值

    方法: 对每个候选相变点t, 取局部窗口[t-w, t+w],
    以"前后均值差的绝对值"为检验统计量,
    通过块Bootstrap零分布（打乱前后分组）生成p值。

    这本质上是块Bootstrap双样本位置检验:
    H0: 该点前后均值无差异 (非相变点)
    H1: 该点前后均值有显著差异 (相变点)

    Args:
        data: 原始时间序列 (T,)
        change_indices: CUSUM检测到的候选相变点索引列表
        n_boot: Bootstrap次数
        block_len: 块长度, 默认 floor(T^(1/3))
        window_factor: 局部窗口宽度 = block_len * window_factor
        seed: 随机种子

    Returns:
        p_values: 与change_indices对应的p值列表 (已做+1连续性校正)
    """
    rng = np.random.default_rng(seed)
    T = len(data)

    if block_len is None:
        block_len = max(2, int(np.round(T ** (1 / 3))))
    block_len = min(block_len, T)

    half_win = max(block_len * window_factor // 2, block_len)
    p_values = []

    for t in change_indices:
        # ── 定义局部窗口 ──
        w_start = max(0, t - half_win)
        w_end = min(T, t + half_win + 1)
        local = data[w_start:w_end]
        rel_t = t - w_start  # t在局部窗口中的位置
        L = len(local)

        if rel_t < block_len or L - rel_t < block_len:
            # 窗口边界不足 → 保守赋p=1
            p_values.append(1.0)
            continue

        # ── 观测统计量 ──
        pre = local[:rel_t]
        post = local[rel_t:]
        obs_stat = abs(np.mean(post) - np.mean(pre))

        # ── 块Bootstrap: 合并前后数据, 打乱分组 ──
        boot_stats = np.zeros(n_boot)
        n_pre = len(pre)
        n_post = len(post)
        n_possible = L - block_len + 1
        blocks_pool = np.array([local[i:i + block_len] for i in range(n_possible)])
        n_blocks_total = max(1, int(np.ceil(L / block_len)))

        for b in range(n_boot):
            idx = rng.integers(0, n_possible, size=n_blocks_total)
            boot_series = np.concatenate(blocks_pool[idx])[:L]
            # 随机划分前/后 (保持原尺寸)
            boot_pre = boot_series[:n_pre]
            boot_post = boot_series[n_pre:n_pre + n_post]
            boot_stats[b] = abs(np.mean(boot_post) - np.mean(boot_pre))

        p_val = float((np.sum(boot_stats >= obs_stat) + 1) / (n_boot + 1))
        p_values.append(p_val)

    return p_values


# ═══════════════════════════════════════════════════════════════
# 3. Benjamini-Hochberg FDR校正
# ═══════════════════════════════════════════════════════════════

def fdr_correction(
    p_values: List[float],
    alpha: float = 0.05,
) -> Dict[str, Any]:
    """Benjamini-Hochberg FDR多重检验校正

    算法:
      1. 将m个p值升序排列: p_(1) ≤ p_(2) ≤ ... ≤ p_(m)
      2. 找到最大k使 p_(k) ≤ α · k / m
      3. 拒绝H0: p_(1), ..., p_(k)

    Args:
        p_values: 原始p值列表 (长度m)
        alpha: 目标FDR水平, 默认0.05

    Returns:
        dict: {
            'significant':      bool列表, 是否经FDR校正后显著,
            'significant_idx':  显著项的原始索引,
            'n_total':          m,
            'n_significant':    校正后显著数,
            'fdr_threshold':    BH阈值 p_(k),
            'k_max':            最大满足条件的k,
        }
    """
    m = len(p_values)
    if m == 0:
        return {
            'significant': [], 'significant_idx': [],
            'n_total': 0, 'n_significant': 0,
            'fdr_threshold': 0.0, 'k_max': 0,
        }

    # 排序并记录原始索引
    p_arr = np.array(p_values)
    sorted_idx = np.argsort(p_arr)
    sorted_p = p_arr[sorted_idx]

    # BH过程: 找到最大k
    k_max = 0
    for k in range(m, 0, -1):
        if sorted_p[k - 1] <= alpha * k / m:
            k_max = k
            break

    significant = np.zeros(m, dtype=bool)
    if k_max > 0:
        significant[sorted_idx[:k_max]] = True

    fdr_threshold = float(alpha * k_max / m) if k_max > 0 else 0.0

    return {
        'significant': significant.tolist(),
        'significant_idx': [int(i) for i in np.where(significant)[0]],
        'n_total': m,
        'n_significant': int(k_max),
        'fdr_threshold': fdr_threshold,
        'k_max': int(k_max),
    }


# ═══════════════════════════════════════════════════════════════
# 4. 一站式CUSUM+Rigor (对外主接口)
# ═══════════════════════════════════════════════════════════════

def cusum_with_rigor(
    data: np.ndarray,
    change_indices: List[int],
    n_boot: int = 1000,
    block_len: Optional[int] = None,
    fdr_alpha: float = 0.05,
    seed: int = 42,
) -> Dict[str, Any]:
    """CUSUM + 块Bootstrap p值 + FDR校正 一站式管道

    使用方式（增量接入，不修改现有CUSUM检测逻辑）:
        changes = cusum_phase_detection(data, ...)       # 现有: 候选点检测
        rigor = cusum_with_rigor(data, changes)           # 新增: 统计严谨性
        fdr_changes = [changes[i] for i in rigor['fdr_significant_idx']]

    Args:
        data: 原始时间序列
        change_indices: CUSUM检测的候选相变点索引 (由外部cusum_phase_detection产生)
        n_boot: Bootstrap次数 (≥500推荐)
        block_len: 块长度, 默认 floor(T^(1/3))
        fdr_alpha: FDR水平
        seed: 随机种子

    Returns:
        dict: {
            'n_candidate':        候选相变点数,
            'p_values':           每个候选点的块Bootstrap p值,
            'fdr_significant':    bool列表, FDR校正后是否显著,
            'fdr_significant_idx': 显著点的change_indices中的索引,
            'n_fdr_significant':  FDR校正后显著点数,
            'fdr_result':         FDR校正完整结果,
            'block_len':          使用的块长度,
            'report_str':         标准报告格式 "N个候选 / M个FDR显著",
        }
    """
    T = len(data)
    if block_len is None:
        block_len = max(2, int(np.round(T ** (1 / 3))))

    n_candidate = len(change_indices)

    if n_candidate == 0:
        return {
            'n_candidate': 0,
            'p_values': [],
            'fdr_significant': [],
            'fdr_significant_idx': [],
            'n_fdr_significant': 0,
            'fdr_result': None,
            'block_len': block_len,
            'report_str': '0个候选 / 0个FDR显著',
        }

    # Step 1: 块Bootstrap p值
    p_values = cusum_block_bootstrap_pvalues(
        data, change_indices, n_boot=n_boot,
        block_len=block_len, seed=seed,
    )

    # Step 2: BH-FDR校正
    fdr_result = fdr_correction(p_values, alpha=fdr_alpha)

    return {
        'n_candidate': n_candidate,
        'p_values': p_values,
        'fdr_significant': fdr_result['significant'],
        'fdr_significant_idx': fdr_result['significant_idx'],
        'n_fdr_significant': fdr_result['n_significant'],
        'fdr_result': fdr_result,
        'block_len': block_len,
        'report_str': f"{n_candidate}个候选 / {fdr_result['n_significant']}个FDR显著",
    }


# ═══════════════════════════════════════════════════════════════
# 5. upgrade_causal() — C1 Granger → C3 SCM 因果升级 (V4.3.1-GA)
# ═══════════════════════════════════════════════════════════════

def upgrade_causal(
    granger_result: Dict[str, Any],
    scm_result: Optional[Dict[str, Any]] = None,
    cause: str = "",
    effect: str = ""
) -> Dict[str, Any]:
    """将 Granger C1 结果与 SCM C3 结果合并，输出统一的因果评级报告。

    这是V4.3.1-GA新增的核心方法，实现用户需求：
    "Granger C1 → SCM C3因果升级方法"

    向后兼容：scm_result=None 时直接返回 Granger 结果（C1标记）

    Args:
        granger_result: Granger因果检验结果字典 (来自CausalityTester.granger())
        scm_result: SCM结构因果推断结果字典 (来自StructuralCausalAnalyzer或SCMAdapter)
        cause: 原因变量名
        effect: 结果变量名

    Returns:
        dict: {
            'cause': str, 'effect': str,
            'granger': { 'f_stat', 'p_value', 'significant', 'grade': 'C1', 'warning' },
            'scm': { 'estimate', 'ci', 'p_value', 'method', 'identification', 'grade', 'refutation_passed' } or None,
            'final_grade': 'C1'|'C2'|'C3'|'C3+',
            'recommendation': str,
        }

    因果证据层级 (CE-C1~C4):
        C1=Predictive (Granger) → C2=Conditional → C3=Counterfactual (SCM) → C4=Mechanistic
    """
    merged = {
        "cause": cause,
        "effect": effect,
        "granger": {
            "f_stat": granger_result.get("granger_y_to_x", {}).get("f_stat", np.nan),
            "p_value": granger_result.get("granger_y_to_x", {}).get("p_value", 1.0),
            "significant": granger_result.get("granger_y_to_x", {}).get("significant", False),
            "grade": "C1",
            "warning": "[Predictive only] — time ordering, not intervention causal",
        },
        "scm": None,
        "final_grade": "C1",
        "recommendation": "Use with caution for policy decisions",
    }

    if scm_result is not None and scm_result.get("validated"):
        scm_grade = scm_result.get("causal_grade", "C2")
        merged["scm"] = {
            "estimate": scm_result.get("estimate", np.nan),
            "ci": [scm_result.get("ci_lower", np.nan), scm_result.get("ci_upper", np.nan)],
            "p_value": scm_result.get("p_value", 1.0),
            "method": scm_result.get("method", "unknown"),
            "identification": scm_result.get("identification", "unknown"),
            "grade": scm_grade,
            "refutation_passed": scm_result.get("refutation_passed", False),
        }

        if scm_grade in ["C3", "C3+"] and scm_result.get("p_value", 1.0) < 0.05:
            merged["final_grade"] = scm_grade
            merged["recommendation"] = (
                "Credible causal claim for policy" if scm_grade == "C3+"
                else "Causal claim with backdoor adjustment"
            )
        elif scm_grade == "C2":
            merged["final_grade"] = "C2"
            merged["recommendation"] = "Conditional independence only — unobserved confounding possible"
    else:
        merged["scm"] = {"status": "not_available", "reason": "SCM adapter not called or failed"}

    return merged


# ═══════════════════════════════════════════════════════════════
# 6. 自检 (模块导入时静默运行)
# ═══════════════════════════════════════════════════════════════

def _self_test():
    """模块自检 — 验证块Bootstrap和FDR的数值正确性"""
    rng = np.random.default_rng(12345)
    T = 200

    # 构造已知变点的序列: 前100点~N(0,1), 后100点~N(2,1)
    data = np.concatenate([
        rng.normal(0, 1, 100),
        rng.normal(2, 1, 100),
    ])

    # 测试1: 块Bootstrap应给出合理的均值CI
    result = block_bootstrap(data, n_boot=500, seed=42)
    assert result['ci_lower'] < np.mean(data) < result['ci_upper'], \
        "块Bootstrap CI应包含样本均值"

    # 测试2: 对已知变点的p值应显著
    known_change = 100
    p_vals = cusum_block_bootstrap_pvalues(
        data, [known_change], n_boot=500, seed=42,
    )
    assert p_vals[0] < 0.05, \
        f"已知变点(t=100, Δμ=2)的块Bootstrap p值应<0.05, 实际={p_vals[0]:.4f}"

    # 测试3: FDR校正 — 模拟m个检验
    p_list = [0.001, 0.01, 0.03, 0.04, 0.20, 0.50, 0.80]
    fdr = fdr_correction(p_list, alpha=0.05)
    assert fdr['n_significant'] >= 2, \
        f"FDR校正应至少保留2个显著(p=0.001,0.01), 实际={fdr['n_significant']}"

    # 测试4: 一站式接口
    rigor = cusum_with_rigor(data, [known_change], n_boot=300, seed=42)
    assert rigor['n_fdr_significant'] == 1, \
        f"已知变点经FDR后应为显著, 实际={rigor['n_fdr_significant']}"
    assert '1个候选' in rigor['report_str'], \
        f"报告格式异常: {rigor['report_str']}"

    return True

# 模块加载时自检
try:
    _SELF_TEST_PASSED = _self_test()
except Exception as e:
    import warnings
    warnings.warn(f"statistical_rigor自检失败: {e}")
    _SELF_TEST_PASSED = False
