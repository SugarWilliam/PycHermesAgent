"""V4.3.1-GA 端到端验证脚本"""
import sys
import traceback

print("=" * 70)
print(" V4.3.1-GA · 端到端验证")
print("=" * 70)

# ── 验证1: 适配器注册表 ──
print("\n[1/6] 适配器注册表...")
try:
    from adapter_registry import list_adapters, get_adapter, adapter_count
    stats = adapter_count()
    print(f"  ✓ 适配器总数: {stats['total']}")
    print(f"  ✓ V4.3.1新增: {stats['new_v431']}")
    print(f"  ✓ 已有适配器: {stats['existing']}")
    print(f"  ✓ 分类统计: {stats['by_category']}")
    assert stats['new_v431'] >= 15, "至少应有15个新适配器"
except Exception as e:
    print(f"  ✗ FAIL: {e}")
    traceback.print_exc()
    sys.exit(1)

# ── 验证2: 关键适配器可导入 ──
print("\n[2/6] 关键适配器导入...")
key_adapters = {
    "A-18": "CausalEmergenceAdapter (EI涌现检测)",
    "A-23": "ABMAdapter (Schelling/意见/知识扩散)",
    "A-12-SCM": "StructuralCausalAnalyzer (结构因果)",
    "A-12-FORECAST": "ForecastAdapter (ARIMA预测)",
    "A-12-BSTS": "BSTSAdapter (贝叶斯因果)",
    "A-22": "NetworkScienceAdapter (网络科学)",
    "A-13": "OrganizationAdapter (组织管理)",
}
for aid, desc in key_adapters.items():
    cls = get_adapter(aid)
    if cls:
        print(f"  ✓ {aid} {desc}")
    else:
        print(f"  ✗ {aid} 未找到!")

# ── 验证3: A-18 CausalEmergenceAdapter EI检测 ──
print("\n[3/6] A-18 CausalEmergenceAdapter EI涌现检测...")
try:
    from complex_systems_adapters import CausalEmergenceAdapter
    import numpy as np
    
    cea = CausalEmergenceAdapter()
    np.random.seed(42)
    # 构造微-宏观数据: 适配器期望 micro_states 为一维状态序列 (>=100)
    np.random.seed(42)
    micro_states = np.random.randint(0, 16, size=500)  # 16 micro-states
    # 粗粒化映射函数: micro -> macro (每4个micro合并为1个macro)
    macro_map_fn = lambda x: x // 4
    
    result = cea(data={
        "micro_states": micro_states,
        "macro_map": macro_map_fn,
    }, params={})
    
    if result.get("validated"):
        print(f"  ✓ EI涌现: macro_EI={result.get('macro_ei', 'N/A')}, "
              f"micro_EI={result.get('micro_ei', 'N/A')}")
        print(f"  ✓ emergence = {result.get('emergence', 'N/A')}, "
              f"has_causal_emergence = {result.get('has_causal_emergence', 'N/A')}")
    else:
        print(f"  ⚠ 返回: {result.get('error', result)}")
except Exception as e:
    print(f"  ✗ FAIL: {e}")
    traceback.print_exc()

# ── 验证4: A-23 ABMAdapter ──
print("\n[4/6] A-23 ABMAdapter Schelling模型...")
try:
    from abm_adapter_v450 import ABMAdapter
    
    abm = ABMAdapter()
    result = abm(data={}, params={
        "model": "schelling",
        "grid_size": 20,
        "n_agents": 200,
        "tolerance": 0.3,
        "n_steps": 50,
        "n_types": 2,
    })
    
    if result.get("validated"):
        seg_idx = result.get('final_segregation_index', 'N/A')
        try:
            seg_str = f"{float(seg_idx):.3f}"
        except (ValueError, TypeError):
            seg_str = str(seg_idx)
        print(f"  ✓ Schelling: 隔离指数={seg_str}, "
              f"收敛步数={result.get('convergence_step', 'N/A')}, "
              f"涌现={result.get('emergence_detected', 'N/A')}")
    else:
        print(f"  ⚠ 返回: {result.get('error', result)}")
except Exception as e:
    print(f"  ✗ FAIL: {e}")
    traceback.print_exc()

# ── 验证5: upgrade_causal() ──
print("\n[5/6] upgrade_causal() C1→C3因果升级...")
try:
    from statistical_rigor import upgrade_causal
    
    # 模拟Granger结果
    granger_res = {
        "granger_y_to_x": {
            "f_stat": 5.34,
            "p_value": 0.008,
            "significant": True,
        }
    }
    
    # 模拟SCM结果
    scm_res = {
        "causal_grade": "C3",
        "estimate": 0.42,
        "ci_lower": 0.15,
        "ci_upper": 0.69,
        "p_value": 0.003,
        "method": "backdoor.ols",
        "identification": "backdoor",
        "refutation_passed": True,
        "validated": True,
    }
    
    merged = upgrade_causal(granger_res, scm_res, cause="CO2", effect="GDP")
    print(f"  ✓ 原因: {merged['cause']} → {merged['effect']}")
    print(f"  ✓ Granger: {merged['granger']['grade']} (p={merged['granger']['p_value']:.4f})")
    print(f"  ✓ SCM: {merged['scm']['grade']} (estimate={merged['scm']['estimate']:.3f})")
    print(f"  ✓ 最终评级: {merged['final_grade']}")
    print(f"  ✓ 建议: {merged['recommendation']}")
    assert merged['final_grade'] == 'C3', f"期望C3, 实际{merged['final_grade']}"
    
    # 测试无SCM时的向后兼容
    merged2 = upgrade_causal(granger_res, cause="X", effect="Y")
    assert merged2['final_grade'] == 'C1', f"无SCM时应为C1, 实际{merged2['final_grade']}"
    print(f"  ✓ 向后兼容: 无SCM时→{merged2['final_grade']}")
except Exception as e:
    print(f"  ✗ FAIL: {e}")
    traceback.print_exc()

# ── 验证6: 新适配器文件完整性 ──
print("\n[6/6] 新适配器文件完整性...")
new_files = [
    "complex_systems_adapters.py",
    "network_science_adapters.py",
    "abm_adapter_v450.py",
    "org_personal_adapters.py",
    "forecast_adapters.py",
    "structural_causal.py",
    "adapter_registry.py",
]
import os
for f in new_files:
    if os.path.exists(f):
        size_kb = os.path.getsize(f) / 1024
        print(f"  ✓ {f} ({size_kb:.1f} KB)")
    else:
        print(f"  ✗ {f} 缺失!")

print("\n" + "=" * 70)
print(" V4.3.1-GA · 端到端验证完成")
print("=" * 70)
