"""
adapter_registry.py — V4.3.1-GA 适配器统一注册表
==================================================
从V4.5.0合入15个新适配器后，建立统一的发现与注册机制，
与V4.5.0的all_adapters.py功能对等，但适配V4.3.0的扁平目录结构。

提供:
  - get_adapter(adapter_id: str) → AdapterClass
  - list_adapters(category: str = None) → List[Dict]
  - ADAPTER_REGISTRY: Dict[str, type]
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Type

logger = logging.getLogger("adapter_registry")

# ═══════════════════════════════════════════════════════════════
# 导入 V4.3.1 新增适配器 (从V4.5.0合入)
# 使用try/except保护可选依赖，允许部分导入失败
# ═══════════════════════════════════════════════════════════════

# 预测与因果适配器 (A-12系列)
try:
    from forecast_adapters import ForecastAdapter, BSTSAdapter, SyntheticControlAdapter
except ImportError as e:
    logger.warning(f"forecast_adapters import failed: {e}")
    ForecastAdapter = BSTSAdapter = SyntheticControlAdapter = None

try:
    from structural_causal import StructuralCausalAnalyzer
except ImportError as e:
    logger.warning(f"structural_causal import failed: {e}")
    StructuralCausalAnalyzer = None

# 组织/个人/团队适配器 (A-13~A-15)
try:
    from org_personal_adapters import OrganizationAdapter, PersonalGrowthAdapter, TeamManagementAdapter
except ImportError as e:
    logger.warning(f"org_personal_adapters import failed: {e}")
    OrganizationAdapter = PersonalGrowthAdapter = TeamManagementAdapter = None

# 复杂系统适配器 (A-16~A-21)
try:
    from complex_systems_adapters import (
        TippingAdapter, SOCAdapter, CausalEmergenceAdapter,
        TransferEntropyAdapter, EvolutionaryAdapter, CoarseGrainingAdapter,
    )
except ImportError as e:
    logger.warning(f"complex_systems_adapters import failed: {e}")
    TippingAdapter = SOCAdapter = CausalEmergenceAdapter = None
    TransferEntropyAdapter = EvolutionaryAdapter = CoarseGrainingAdapter = None

# 网络科学适配器 (A-22)
try:
    from network_science_adapters import NetworkScienceAdapter
except ImportError as e:
    logger.warning(f"network_science_adapters import failed: {e}")
    NetworkScienceAdapter = None

# ABM适配器 (A-23)
try:
    from abm_adapter_v450 import ABMAdapter
except ImportError as e:
    logger.warning(f"abm_adapter_v450 import failed: {e}")
    ABMAdapter = None

# ═══════════════════════════════════════════════════════════════
# 尝试导入 V4.3.0 已有适配器 (基础设施占位符)
# ═══════════════════════════════════════════════════════════════
_EXISTING_REGISTRY: Dict[str, Type] = {}
try:
    from infrastructure_adapters import ADAPTER_REGISTRY as _INFRA_REGISTRY
    _EXISTING_REGISTRY.update(_INFRA_REGISTRY)
except ImportError:
    logger.warning("infrastructure_adapters.ADAPTER_REGISTRY 不可用")

# ═══════════════════════════════════════════════════════════════
# 统一注册表
# ═══════════════════════════════════════════════════════════════

ADAPTER_REGISTRY: Dict[str, Type] = {}

# 仅添加成功导入的适配器
_PENDING_REGISTRY = {
    # ── A-12 预测与因果系列 ──
    "A-12-FORECAST": ForecastAdapter,
    "A-12-BSTS": BSTSAdapter,
    "A-12-SYNTH": SyntheticControlAdapter,
    "A-12-SCM": StructuralCausalAnalyzer,

    # ── A-13~A-15 组织/个人/团队 ──
    "A-13": OrganizationAdapter,
    "A-14": PersonalGrowthAdapter,
    "A-15": TeamManagementAdapter,

    # ── A-16~A-21 复杂系统 ──
    "A-16": TippingAdapter,
    "A-17": SOCAdapter,
    "A-18": CausalEmergenceAdapter,
    "A-19": TransferEntropyAdapter,
    "A-20": EvolutionaryAdapter,
    "A-21": CoarseGrainingAdapter,

    # ── A-22 网络科学 ──
    "A-22": NetworkScienceAdapter,

    # ── A-23 ABM ──
    "A-23": ABMAdapter,
}

for _id, _cls in _PENDING_REGISTRY.items():
    if _cls is not None:
        ADAPTER_REGISTRY[_id] = _cls

# 合并已有适配器（使用编号前缀区分，避免冲突）
for _id, _cls in _EXISTING_REGISTRY.items():
    if _id not in ADAPTER_REGISTRY:
        ADAPTER_REGISTRY[_id] = _cls

# ═══════════════════════════════════════════════════════════════
# 适配器分类信息
# ═══════════════════════════════════════════════════════════════

ADAPTER_CATEGORIES = {
    "预测与因果": ["A-12-FORECAST", "A-12-BSTS", "A-12-SYNTH", "A-12-SCM"],
    "组织/个人/团队": ["A-13", "A-14", "A-15"],
    "复杂系统": ["A-16", "A-17", "A-18", "A-19", "A-20", "A-21"],
    "网络科学": ["A-22"],
    "ABM智能体": ["A-23"],
    "基础设施": list(_EXISTING_REGISTRY.keys()),
}

# ═══════════════════════════════════════════════════════════════
# 公共接口
# ═══════════════════════════════════════════════════════════════

def get_adapter(adapter_id: str) -> Optional[Type]:
    """根据adapter_id获取适配器类
    
    Args:
        adapter_id: 适配器标识符，如 "A-18", "A-12-SCM"
        
    Returns:
        Adapter class or None
    """
    return ADAPTER_REGISTRY.get(adapter_id)


def list_adapters(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """列出所有注册适配器
    
    Args:
        category: 可选分类过滤
        
    Returns:
        适配器信息列表，每项含 {id, name, version, disciplines, theories, category}
    """
    result = []
    
    # 确定要列出的适配器ID
    if category:
        ids = ADAPTER_CATEGORIES.get(category, [])
    else:
        ids = list(ADAPTER_REGISTRY.keys())
    
    for aid in ids:
        cls = ADAPTER_REGISTRY.get(aid)
        if cls is None:
            continue
        
        # 确定分类
        cat = category or "未分类"
        if category is None:
            for cat_name, cat_ids in ADAPTER_CATEGORIES.items():
                if aid in cat_ids:
                    cat = cat_name
                    break
        
        # 提取元信息
        name = getattr(cls, '__name__', str(cls))
        version = getattr(cls, 'version', 'unknown')
        disciplines = getattr(cls, 'disciplines', [])
        theories = getattr(cls, 'theories', [])
        
        result.append({
            'id': aid,
            'name': name,
            'version': version,
            'disciplines': disciplines,
            'theories': theories,
            'category': cat,
        })
    
    return result


def adapter_count() -> Dict[str, int]:
    """统计适配器数量
    
    Returns:
        {'total': n, 'new_v431': n, 'existing': n, 'by_category': {...}}
    """
    new_ids = [
        "A-12-FORECAST", "A-12-BSTS", "A-12-SYNTH", "A-12-SCM",
        "A-13", "A-14", "A-15",
        "A-16", "A-17", "A-18", "A-19", "A-20", "A-21",
        "A-22", "A-23",
    ]
    
    by_cat = {}
    for cat_name, cat_ids in ADAPTER_CATEGORIES.items():
        by_cat[cat_name] = len([i for i in cat_ids if i in ADAPTER_REGISTRY])
    
    return {
        'total': len(ADAPTER_REGISTRY),
        'new_v431': len([i for i in new_ids if i in ADAPTER_REGISTRY]),
        'existing': len(_EXISTING_REGISTRY),
        'by_category': by_cat,
    }


# ═══════════════════════════════════════════════════════════════
# 自检
# ═══════════════════════════════════════════════════════════════
def _self_test():
    """模块自检"""
    stats = adapter_count()
    assert stats['new_v431'] >= 15, f"应有至少15个新适配器, 实有{stats['new_v431']}"
    
    # 验证关键适配器可获取
    assert get_adapter("A-18") is not None, "A-18 CausalEmergenceAdapter 未注册"
    assert get_adapter("A-23") is not None, "A-23 ABMAdapter 未注册"
    assert get_adapter("A-12-SCM") is not None, "A-12-SCM StructuralCausalAnalyzer 未注册"
    
    adapters = list_adapters()
    assert len(adapters) > 0, "适配器列表不应为空"
    
    # 分类过滤
    cs_adapters = list_adapters("复杂系统")
    assert len(cs_adapters) >= 6, f"复杂系统应有至少6个适配器, 实有{len(cs_adapters)}"
    
    return True


try:
    _SELF_TEST_PASSED = _self_test()
except Exception as e:
    import warnings
    warnings.warn(f"adapter_registry自检失败: {e}")
    _SELF_TEST_PASSED = False
