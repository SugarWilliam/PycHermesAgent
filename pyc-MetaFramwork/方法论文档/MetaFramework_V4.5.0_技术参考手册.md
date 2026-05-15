# MetaFramework V4.5.0-GA 技术参考手册

> **副标题**：跨学科数学建模方法论体系 — 第一部与第二部补丁合入主文档
>
> **作者**：MetaFramework Research Group
> **机构**：Cross-Disciplinary Mathematical Modeling Methodology System
> **版本**：V4.5.0 General Availability
> **日期**：2026年5月

---

## 目录

- [第一篇 总览与架构](#第一篇-总览与架构)
  - [1.1 版本演进](#11-版本演进)
  - [1.2 六步调用链](#12-六步调用链)
  - [1.3 因果证据层级](#13-因果证据层级)
  - [1.4 适配器总览](#14-适配器总览)
- [第二篇 第一部补丁](#第二篇-第一部补丁-v431v440)
  - [2.1 SCMAdapter](#21-scmadapter-a-9-ext)
  - [2.2 ForecastAdapter](#22-forecastadapter-a-12-forecast)
  - [2.3 BSTSAdapter](#23-bstsadapter-a-12-bsts)
  - [2.4 SyntheticControlAdapter](#24-syntheticcontroladapter-a-12-synth)
  - [2.5 upgrade_causal()](#25-frameworkupgradecausal)
- [第三篇 第二部补丁](#第三篇-第二部补丁-v440v450)
  - [3.1 OrganizationAdapter](#31-organizationadapter-a-13)
  - [3.2 PersonalGrowthAdapter](#32-personalgrowthadapter-a-14)
  - [3.3 TeamManagementAdapter](#33-teammanagementadapter-a-15)
  - [3.4 v2极限版](#34-v2极限版适配器)
  - [3.5 TippingAdapter](#35-tippingadapter-a-16)
  - [3.6 SOCAdapter](#36-socadapter-a-17)
  - [3.7 CausalEmergenceAdapter](#37-causalemergenceadapter-a-18)
  - [3.8 TransferEntropyAdapter](#38-transferentropyadapter-a-19)
  - [3.9 EvolutionaryAdapter](#39-evolutionaryadapter-a-20)
  - [3.10 CoarseGrainingAdapter](#310-coarsegrainingadapter-a-21)
  - [3.11 NetworkScienceAdapter](#311-networkscienceadapter-a-22)
  - [3.12 ABMAdapter](#312-abmadapter-a-23)
- [第四篇 API参考手册](#第四篇-api参考手册)
  - [4.1 MetaFramework核心类](#41-metaframework-核心类)
  - [4.2 适配器统一接口](#42-适配器统一接口)
  - [4.3 数据获取模块](#43-数据获取模块)
  - [4.4 统计模块](#44-统计模块)
- [第五篇 安装与部署](#第五篇-安装与部署)
  - [5.1 依赖清单](#51-依赖清单)
  - [5.2 快速安装](#52-快速安装)
  - [5.3 验证测试](#53-验证测试)
- [第六篇 补丁变更日志](#第六篇-补丁变更日志)
  - [6.1 v4.3.1变更](#61-v431补丁变更)
  - [6.2 v4.4.0变更](#62-v440补丁变更)
  - [6.3 v4.5.0变更](#63-v450补丁变更)

---

# 第一篇 总览与架构

## 1.1 版本演进

MetaFramework是一个跨学科数学建模方法论体系，旨在为复杂系统分析提供统一的方法论框架。版本演进如下：

**版本演进历史**

| 版本 | 代号 | 日期 | 核心特性 |
| --- | --- | --- | --- |
| v4.0.0 | GA | 2026-04 | 基础框架，9个核心适配器，六步调用链，C1-C4因果层级 |
| v4.3.0 | GA | 2026-04 | 新增SCM因果推断，MBB+FDR统计层，50/50验证范式 |
| v4.3.1 | PATCH | 2026-04 | **第一部补丁**：SCM增强 + 预测增强（ARIMA/BSTS/Synth） |
| v4.4.0 | PATCH | 2026-05 | 组织/个人/团队管理扩展（A-13~A-15）+ v2极限版 |
| v4.5.0 | GA | 2026-05 | **第二部补丁**：复杂系统理论极限覆盖（A-16~A-23）+ 多领域验证 |

## 1.2 六步调用链

MetaFramework的核心分析流程由六个严格衔接的步骤组成，任何分析任务必须依次通过六步调用链：

**六步调用链说明**

| 步骤 | 名称 | 功能 | 输出 |
| --- | --- | --- | --- |
| Step 1 | 理论选择 | 基于数据特征匹配复杂系统理论 | 理论清单 |
| Step 2 | 参数校准 | 使用真实数据校准模型参数 | 校准报告 |
| Step 3 | 适配器调用 | 调用专用适配器执行分析 | 分析结果 |
| Step 4 | 跨尺度耦合 | 整合微观-中观-宏观三个尺度 | 耦合报告 |
| Step 5 | 扰动测试 | 设计反事实情景测试鲁棒性 | 敏感性分析 |
| Step 6 | 报告输出 | 生成因果证据评级与战略建议 | 最终报告 |

## 1.3 因果证据层级 (C1-C4)

MetaFramework采用四级因果证据标准，任何分析结论必须明确标注其因果层级：

**因果证据层级标准**

| 层级 | 名称 | 方法 | 置信度 |
| --- | --- | --- | --- |
| C1 | 预测性证据 | 相关性分析、趋势预测、ARIMA | 低 |
| C2 | 条件独立性 | 传递熵、Granger检验、PC算法 | 中低 |
| C3 | 可识别因果 | ABM反事实、合成控制、BSTS | 中高 |
| C4 | 干预因果 | DID、RDD、IV、真实实验 | 高 |

> ⚠️ **注意**: **注意**：默认情况下框架输出C1-C3层级证据。C4需要真实政策干预数据，通常在分析完成后的追踪研究中获得。upgrade_causal()方法可将C2/C3证据升级至更高层级。

## 1.4 适配器总览 (23个)

**全部23个适配器一览**

| ID | 适配器 | 类别 | 核心方法 | 适用场景 |
| --- | --- | --- | --- | --- |
| A-1 | ClimateAdapter | 基础 | 气候情景分析 | 碳排放、温度路径 |
| A-2 | ExtremeValueAdapter | 基础 | 极值理论(GEV) | 极端天气、金融风险 |
| A-3 | EpidemiologyAdapter | 基础 | SIR/SEIR模型 | 传染病传播 |
| A-4 | CognitionAdapter | 基础 | 认知负荷模型 | 决策心理 |
| A-5 | PolicyFeedbackAdapter | 基础 | 政策效应滞后模型 | 政策评估 |
| A-6 | EconometricsAdapter | 基础 | VAR/面板数据 | 宏观经济 |
| A-7 | EnergyEconomicsAdapter | 基础 | 能源系统优化 | 能源转型 |
| A-8 | DamageFunctionAdapter | 基础 | 气候损失函数 | 气候经济 |
| A-9-EXT | SCMAdapter | 第一部补丁 | 结构因果模型(IV/SEM) | 因果推断增强 |
| A-12-FORECAST | ForecastAdapter | 第一部补丁 | ARIMA滚动预测 | 时序预测 |
| A-12-BSTS | BSTSAdapter | 第一部补丁 | 贝叶斯结构时序 | 因果时序 |
| A-12-SYNTH | SyntheticControlAdapter | 第一部补丁 | 合成控制法 | 政策评估 |
| A-13 | OrganizationAdapter | 第二部补丁 | EVM/Churn/DiD | 组织分析 |
| A-14 | PersonalGrowthAdapter | 第二部补丁 | 学习曲线/习惯养成 | 个人成长 |
| A-15 | TeamManagementAdapter | 第二部补丁 | 生产力分解/冲突检测 | 团队管理 |
| A-16 | TippingAdapter | 第二部补丁 | 临界慢化检测(CSD) | 临界点预警 |
| A-17 | SOCAdapter | 第二部补丁 | 自组织临界性 | 灾害/市场崩盤 |
| A-18 | CausalEmergenceAdapter | 第二部补丁 | 有效信息(EI) | 涌现性检验 |
| A-19 | TransferEntropyAdapter | 第二部补丁 | 传递熵 | 信息流方向 |
| A-20 | EvolutionaryAdapter | 第二部补丁 | 复制动力学 | 演化博弈 |
| A-21 | CoarseGrainingAdapter | 第二部补丁 | 多尺度粗粒化 | 尺度转换 |
| A-22 | NetworkScienceAdapter | 第二部补丁 | 渗流/PageRank | 网络分析 |
| A-23 | ABMAdapter | 第二部补丁 | 智能体模拟 | 政策模拟 |

============ PART 2 ============
---

# 第二篇 第一部补丁 (v4.3.1→v4.4.0)

第一部补丁于2026年4月发布，核心目标是**增强根因分析能力**和**预测能力**，使框架从"解释过去"扩展到"预测未来+识别因果"。包含4个新增适配器和1个核心方法升级。

## 2.1 SCMAdapter (A-9-EXT)

SCMAdapter是第一部补丁中最核心的组件，它通过结构因果模型（Structural Causal Model）方法增强了框架的根因分析能力。该适配器使用linearmodels/statsmodels直接实现IV（工具变量）和2SLS估计，避免了DoWhy的版本兼容性问题。

```python
SCMAdapter(data, params)

data

: {iv_regime, iv_design, endogenous, instruments, controls, outcome, treatment, observed_data, dag_edges}
params

: {stage, alpha, use_cluster, method}
returns

: {causal_estimate, std_error, p_value, ci_lower, ci_upper, r_squared, method, interpretation, evidence_grade}
```

### 核心方法

**IV估计（工具变量法）**

IV估计用于处理内生性问题，当解释变量与误差项相关时，通过工具变量获取一致的因果效应估计。数学表达：

第一阶段：X = π₀ + π₁Z + π₂W + v

第二阶段：Y = β₀ + β₁X̂ + β₂W + ε

其中Z为工具变量，W为控制变量，X̂为第一阶段预测值。

```python
from metamodel.adapters.all_adapters import SCMAdapter

adapter = SCMAdapter()
result = adapter(data={
    "iv_regime": True,
    "iv_design": {
        "endogenous": "education",
        "instruments": ["distance_to_college"],
        "controls": ["age", "gender"],
    },
    "outcome": "income",
    "treatment": "education",
    "observed_data": df.to_dict("records"),
}, params={"stage": "full", "alpha": 0.05})

print(f"因果效应: {result['causal_estimate']}")
print(f"证据等级: {result['evidence_grade']}")  # 输出 C3
```

### 证据升级路径

SCMAdapter的输出默认为C3（可识别因果）。当满足以下条件时可升级至C4：

- 工具变量外生性通过过度识别检验（Sargan/Hansen J统计量）
- 样本量>1000且不存在弱工具变量问题（F统计量>10）
- 效应方向在多个子样本中保持一致

## 2.2 ForecastAdapter (A-12-FORECAST)

ForecastAdapter提供ARIMA滚动预测+概率置信区间，用于生成未来时序的预测分布，为决策提供不确定性量化。

```python
ForecastAdapter(data, params)

data

: {series, dates, exog}
params

: {horizon, alpha, model_type, auto_select}
returns

: {forecast_mean, forecast_ci, model_params, mape, rmse, aic, bic}
```

### 核心方法

**滚动ARIMA预测**

采用"滚动窗口"策略：每次预测后，将实际观测值加入训练集，重新拟合模型并预测下一期。这避免了模型漂移问题。

```python
from metamodel.adapters.forecast_adapters import ForecastAdapter

adapter = ForecastAdapter()
result = adapter(data={
    "series": gdp_series,
    "dates": date_list,
}, params={
    "horizon": 5,
    "alpha": 0.05,
    "model_type": "auto_arima",
    "auto_select": True,
})

print(f"预测均值: {result['forecast_mean']}")
print(f"95%置信区间: {result['forecast_ci']}")
print(f"MAPE: {result['mape']:.2f}%")
```

## 2.3 BSTSAdapter (A-12-BSTS)

BSTSAdapter实现贝叶斯结构时序因果推断，基于Brodersen et al. (2015)的BSTS方法，通过贝叶斯模型平均处理时间序列中的因果效应识别。

```python
BSTSAdapter(data, params)

data

: {time_series, intervention_date, pre_period, post_period, covariates}
params

: {niter, burn, prior_level_sd, seasonal_periods}
returns

: {causal_effect, posterior_ci, probability_of_effect, pre_mape, cumulated_effect}
```

### 核心方法

BSTS使用状态空间模型分解时间序列：

y_t = μ_t + τ_t + s_t + ε_t

其中μ_t为趋势，τ_t为干预效应，s_t为季节性，ε_t为噪声。通过MCMC采样获取后验分布，计算干预的因果效应。

```python
from metamodel.adapters.forecast_adapters import BSTSAdapter

adapter = BSTSAdapter()
result = adapter(data={
    "time_series": monthly_data,
    "intervention_date": "2024-01",
    "pre_period": ["2020-01", "2023-12"],
    "post_period": ["2024-01", "2024-12"],
}, params={"niter": 5000, "burn": 1000})

print(f"因果效应: {result['causal_effect']}")
print(f"效应概率: {result['probability_of_effect']:.2%}")
```

## 2.4 SyntheticControlAdapter (A-12-SYNTH)

SyntheticControlAdapter实现Abadie et al. (2010)的合成控制法，通过SLSQP优化构建加权合成控制组，用于评估政策干预的因果效应。

```python
SyntheticControlAdapter(data, params)

data

: {treated_unit, control_units, pre_period, post_period, predictors, outcome}
params

: {optimization_method, placebo_tests, n_placebo}
returns

: {weights, gap, pre_rmspe, post_rmspe, ratio, p_value, synthetic_series}
```

### 核心方法

合成控制法通过求解以下优化问题构建合成单元：

min_w ||X₁ - X₀w||²  s.t. w_i ≥ 0, Σw_i = 1

其中X₁为受干预单元的特征向量，X₀为控制池的特征矩阵，w为最优权重。

```python
from metamodel.adapters.forecast_adapters import SyntheticControlAdapter

adapter = SyntheticControlAdapter()
result = adapter(data={
    "treated_unit": "Nanchang",
    "control_units": ["Changsha", "Hefei", "Zhengzhou"],
    "pre_period": ["2019", "2023"],
    "post_period": ["2024", "2025"],
}, params={"optimization_method": "SLSQP", "placebo_tests": True})

print(f"合成权重: {result['weights']}")
print(f"效应显著性: p={result['p_value']:.3f}")
```

## 2.5 framework.upgrade_causal()

upgrade_causal()是第一部补丁在framework.py中追加的核心方法，用于将低层级因果证据升级至更高层级。

```python
MetaFramework.upgrade_causal(current_grade, target_grade, evidence_pool)

current_grade

: str — 当前证据等级 ("C1"|"C2"|"C3")
target_grade

: str — 目标等级 ("C2"|"C3"|"C4")
evidence_pool

: dict — 证据池 {prediction, independence, identification, intervention}
returns

: dict — {upgraded_grade, confidence, missing_evidence, recommendations}
```

### 升级规则

**证据升级路径**

| 当前 | 目标 | 所需额外证据 | 方法 |
| --- | --- | --- | --- |
| C1 | C2 | 条件独立性检验 | 传递熵/Granger/PC算法 |
| C2 | C3 | 反事实识别 | ABM/BSTS/合成控制 |
| C3 | C4 | 真实干预数据 | DID/RDD/IV |

```python
from metamodel.core.framework import MetaFramework

mf = MetaFramework()
upgrade = mf.upgrade_causal(
    current_grade="C2",
    target_grade="C3",
    evidence_pool={
        "prediction": pred_result,
        "independence": te_result,
    }
)

print(f"升级后等级: {upgrade['upgraded_grade']}")
print(f"置信度: {upgrade['confidence']}")
print(f"缺失证据: {upgrade['missing_evidence']}")
```

============ PART 3 ============
---

# 第三篇 第二部补丁 (v4.4.0→v4.5.0)

第二部补丁于2026年5月发布，核心目标是**将可解范围扩大至组织和项目分析、个人成长、公司和团队管理**，并**补齐复杂系统理论的8个缺失领域**，达到"微观-中观-宏观"全尺度覆盖。

## 3.1 OrganizationAdapter (A-13)

OrganizationAdapter扩展MetaFramework至组织与项目分析领域，实现挣值管理(EVM)、员工流失预测(Churn)、组织变革效果评估(DiD)等功能。

```python
OrganizationAdapter(data, params)

data

: {analysis_type, project_data, employee_data, change_data}
params

: {analysis_type, alpha, forecast_horizon}
returns

: dict — 依analysis_type返回不同结构
```

### 三种分析模式

**A-13分析模式**

| 模式 | 方法 | 输出 | 适用场景 |
| --- | --- | --- | --- |
| evm | 挣值管理 | SV, CV, SPI, CPI, EAC, VAC | 项目进度/成本控制 |
| churn | 生存分析(Cox) + RDD | 风险评分, 阈值效应, 保留建议 | 员工流失预警 |
| change | 双重差分(DiD) | ATT, 显著性, 趋势对比 | 组织变革评估 |

```python
from metamodel.adapters.org_personal_adapters import OrganizationAdapter

# EVM项目分析
adapter = OrganizationAdapter()
result = adapter(data={
    "analysis_type": "evm",
    "project_data": {
        "planned_value": [100, 200, 300],
        "earned_value": [90, 210, 280],
        "actual_cost": [110, 190, 320],
    }
}, params={"analysis_type": "evm"})

print(f"SPI: {result['spi']:.2f}")
print(f"CPI: {result['cpi']:.2f}")
```

## 3.2 PersonalGrowthAdapter (A-14)

PersonalGrowthAdapter扩展至个人成长领域，实现学习曲线拟合、习惯养成模型(HMM)、目标达成预测(Kalman滤波)等功能。

```python
PersonalGrowthAdapter(data, params)

data

: {analysis_type, learning_data, habit_data, goal_data}
params

: {analysis_type, model_type}
returns

: dict — 依analysis_type返回不同结构
```

### 三种分析模式

**A-14分析模式**

| 模式 | 方法 | 输出 | 适用场景 |
| --- | --- | --- | --- |
| learning | 学习曲线(Wright/Crawford) | 曲线参数, 平台期, 学习效率 | 技能习得分析 |
| habit | 隐马尔可夫模型(HMM) | 状态转移矩阵, 稳态分布, 干预效果 | 习惯养成追踪 |
| goal | Kalman滤波 | 达成概率, 时间预测, 里程碑 | 目标管理 |

## 3.3 TeamManagementAdapter (A-15)

TeamManagementAdapter扩展至团队管理领域，实现生产力分解(DEA)、冲突检测(社会网络)、最优团队规模(排队论)等功能。

```python
TeamManagementAdapter(data, params)

data

: {analysis_type, productivity_data, interaction_data, task_data}
params

: {analysis_type, model_type}
returns

: dict — 依analysis_type返回不同结构
```

### 三种分析模式

**A-15分析模式**

| 模式 | 方法 | 输出 | 适用场景 |
| --- | --- | --- | --- |
| productivity | DEA(数据包络分析) | 效率分数, 前沿面, 改进方向 | 团队效率评估 |
| conflict | 社会网络分析(SNA) | 派系检测, 桥梁节点, 冲突指数 | 团队关系诊断 |
| optimal_size | 排队论(M/M/c) | 最优人数, 等待时间, 吞吐量 | 团队规模决策 |

## 3.4 v2极限版适配器

v2极限版适配器是对A-13~A-15的增强版本，采用更高级的方法论，达到理论和知识的极限覆盖：

**v2极限版适配器**

| 基础适配器 | v2极限版方法 | 增强点 |
| --- | --- | --- |
| A-13 Churn | Cox生存分析 + RDD | 时间依赖风险 + 政策断点效应 |
| A-13 Change | Synth-DiD | 合成控制 + DiD结合 |
| A-14 Habit | HMM + 时变转移 | 习惯状态动态演化 |
| A-14 Goal | Kalman + 自适应噪声 | 目标跟踪更鲁棒 |
| A-15 Productivity | Network-DEA | 网络关联效率分析 |
| A-15 Conflict | 多层网络 + 级联模型 | 跨层级冲突传播 |
| A-15 OptimalSize | M/G/c + 学习效应 | 更符合实际服务时间分布 |

## 3.5 TippingAdapter (A-16)

TippingAdapter基于Dakos et al. (2008)的临界慢化理论，检测系统是否接近临界点。通过计算AR1系数、方差趋势和返回率三个指标，提供早期预警。

```python
TippingAdapter(data, params)

data

: {series, detection_method, window_size, lag}
params

: {window_size, significance_level}
returns

: {variance_trend, ar1_value, return_rate, early_warning, p_value}
```

### 核心指标

**CSD检测指标**

| 指标 | 临界点趋近信号 | 物理意义 |
| --- | --- | --- |
| AR1 | → 1.0 | 系统恢复力下降 |
| 方差 | 增大 | 波动增强 |
| 返回率 | → 0 | 记忆效应增强 |

## 3.6 SOCAdapter (A-17)SOCAdapter基于Bak-Tang-Wiesenfeld (1987)的自组织临界性理论，模拟沙堆模型和(branching process)级联过程，分析系统自组织至临界状态的特性。

```python
SOCAdapter(data, params)

data

: {model_type, grid_size, n_steps, branching_ratio}
params

: {threshold, p_trigger, n_sites}
returns

: {event_sizes, event_durations, power_law_exponent, branching_ratio}
```

## 3.7 CausalEmergenceAdapter (A-18)

CausalEmergenceAdapter基于Hoel et al. (2013)的有效信息(Effective Information)框架，检验宏观态是否比微观态具有更高的因果效力，从而检测因果涌现。

```python
CausalEmergenceAdapter(data, params)

data

: {micro_states, macro_states}
params

: {bins, n_shuffle}
returns

: {EI, EI_macro, EI_micro, emergence, p_value}
```

> ⚠️ **注意**: **v4.5.0-GA修复**：此适配器在v4.5.0-GA中修复了多维状态输入时np.unique()报unhashable type的bug。现在支持多维向量micro_states输入。

### 涌现判定

E_macro > E_micro 且 p < 0.05 时，判定存在正向因果涌现。

## 3.8 TransferEntropyAdapter (A-19)

TransferEntropyAdapter基于Schreiber (2000)的传递熵理论，量化两个时间序列之间的定向信息传递，识别信息流方向和强度。

```python
TransferEntropyAdapter(data, params)

data

: {source, target}
params

: {n_bins, lag, n_shuffle}
returns

: {transfer_entropy, significance, direction, surrogate_ci}
```

## 3.9 EvolutionaryAdapter (A-20)

EvolutionaryAdapter基于Weibull (1995)的演化博弈理论，实现复制动力学模拟和进化稳定策略(ESS)检测，分析群体策略演化。

```python
EvolutionaryAdapter(data, params)

data

: {model_type, payoff_matrix, initial_frequencies, n_strategies}
params

: {t_max, dt}
returns

: {equilibrium, is_ess, ess_strategy, trajectory, has_cyclic_dynamics}
```

## 3.10 CoarseGrainingAdapter (A-21)

CoarseGrainingAdapter实现多尺度粗粒化分析，通过微观-介观-宏观三层映射，量化不同尺度下的有效信息损失和涌现。

```python
CoarseGrainingAdapter(data, params)

data

: {micro_data, method, n_levels}
params

: {n_levels, method}
returns

: {macro_data, n_levels, method, order_parameters, scaling_exponent, emergence}
```

## 3.11 NetworkScienceAdapter (A-22)

NetworkScienceAdapter提供网络科学分析工具，包括渗流相变、PageRank中心性、级联失效和鲁棒性分析。

```python
NetworkScienceAdapter(data, params)

data

: {network_type, adjacency, analysis_type, initial_load}
params

: {threshold_range, damping, tolerance}
returns

: dict — 依analysis_type返回不同结构
```

### 四种分析模式

**A-22分析模式**

| 模式 | 方法 | 输出 |
| --- | --- | --- |
| percolation | 渗流相变 | p_critical, max_component_sizes |
| pagerank | PageRank | pagerank, eigenvalue |
| cascading_failure | 级联失效 | failed_nodes, cascade_size |
| robustness | 鲁棒性分析 | robustness_curve |

## 3.12 ABMAdapter (A-23)

ABMAdapter是智能体模拟引擎，实现知识扩散、Bass扩散、意见动力学和Schelling隔离等经典ABM模型。

```python
ABMAdapter(data, params)

data

: {model_type, n_agents, n_steps, spatial_weights}
params

: {learning_rate, innovation_prob, network_density}
returns

: {final_avg_knowledge, final_max_knowledge, n_innovations, time_series}
```

### 模型类型

**A-23模型类型**

| 模型 | 描述 | 适用场景 |
| --- | --- | --- |
| schelling | 隔离模型 | 居住隔离、市场分割 |
| opinion | 意见动力学(HK模型) | 舆论演化、极化 |
| knowledge_diffusion | 知识扩散 | 创新扩散、技术传播 |
| bass_diffusion | Bass产品扩散 | 新产品市场渗透 |
| custom | 自定义模型 | 用户定义规则 |

============ PART 4 ============
---

# 第四篇 API参考手册

## 4.1 MetaFramework 核心类

```python
class MetaFramework(version="4.5.0-GA")
```

### 核心方法

```python
class MetaFramework:
    """MetaFramework V4.5.0-GA 核心类"""

    def __init__(self, version="4.5.0-GA"):
        self.version = version
        self.data_fetcher = DataFetcher()
        self.stats = RobustStatsModule()
        self.coupler = CrossScaleCoupler()
        self.adapters = {}
        self._register_all_adapters()

    def run(self, scenario_data, scenario_params,
            chain_mode="full"):
        """六步调用链主入口"""
        # Step 1: 理论选择
        theories = self._select_theories(scenario_data)

        # Step 2: 参数校准
        calibrated = self._calibrate(scenario_data, scenario_params)

        # Step 3: 适配器调用
        results = self._call_adapters(calibrated, scenario_params)

        # Step 4: 跨尺度耦合
        coupled = self.coupler.couple(results)

        # Step 5: 扰动测试
        robust = self._perturbation_test(coupled)

        # Step 6: 报告输出
        report = self._generate_report(robust)

        return report

    def upgrade_causal(self, current_grade, target_grade,
                        evidence_pool):
        """因果证据升级方法 (第一部补丁)"""
        # 升级逻辑...
        return upgraded_result

    def verify_scm_patches(self, data):
        """验证SCM补丁安装 (第一部补丁)"""
        # 验证逻辑...
        return verification_result
```

## 4.2 适配器统一接口

所有适配器遵循统一的调用接口：

```python
class BaseAdapter:
    """适配器基类"""

    adapter_id = "BASE"       # 适配器ID
    adapter_name = "Base"     # 适配器名称
    version = "1.0"           # 版本

    def __call__(self, data, params):
        """统一调用接口

        Args:
            data: dict — 输入数据
            params: dict — 分析参数

        Returns:
            dict — 分析结果
        """
        self.data = data
        self.params = params
        return self.analyze()

    def analyze(self):
        """子类必须实现此方法"""
        raise NotImplementedError
```

### 结果返回规范

所有适配器返回的字典必须包含以下标准字段：

**标准返回字段**

| 字段 | 类型 | 说明 | 必需 |
| --- | --- | --- | --- |
| causal_estimate | float | 因果效应估计值 | 是 |
| std_error | float | 标准误 | 是 |
| p_value | float | p值 | 是 |
| ci_lower | float | 置信区间下限 | 是 |
| ci_upper | float | 置信区间上限 | 是 |
| evidence_grade | str | 证据等级(C1-C4) | 是 |
| interpretation | str | 结果解读 | 是 |
| model_info | dict | 模型诊断信息 | 可选 |

## 4.3 数据获取模块

```python
class DataFetcher
```

DataFetcher提供统一的数据获取接口，支持从多个数据源获取真实数据：

```python
class DataFetcher:
    """数据获取器"""

    def fetch(self, source, params):
        """通用数据获取

        Args:
            source: str — 数据源标识
            params: dict — 获取参数

        Returns:
            pd.DataFrame — 获取的数据
        """

    def fetch_real_data(self, scenario_type,
                        use_api=True,
                        fallback_stats=True):
        """获取真实数据 (带统计特征回退)

        如果API调用失败，自动回退到基于统计特征参数校准的数据。

        Args:
            scenario_type: str — 场景类型
            use_api: bool — 是否尝试API
            fallback_stats: bool — 是否启用统计回退
        """

    def build_synthetic_data(self, stat_profile, n_samples):
        """基于统计特征构建合成数据"""
        # 使用对数正态分布匹配真实数据的统计特征
```

## 4.4 统计模块

```python
class RobustStatsModule
```

RobustStatsModule提供稳健的统计检验和前提检查：

**统计模块功能**

| 方法 | 功能 | 适用场景 |
| --- | --- | --- |
| check_stationarity() | ADF/KPSS检验 | 时间序列前提 |
| check_granger_prerequisites() | 平稳性+协整检验 | Granger因果前提 |
| mwhitney_test() | Mann-Whitney U检验 | 非参数差异检验 |
| mc_p_value() | Monte Carlo p值 | 复杂统计量检验 |
| jackknife_ci() | 刀切法置信区间 | 稳健区间估计 |
| bca_bootstrap() | BCa Bootstrap | 偏差校正区间 |
| check_instruments() | 弱工具变量检验 | IV诊断 |

============ PART 5 ============
---

# 第五篇 安装与部署

## 5.1 依赖清单

**外部依赖**

| 包名 | 版本 | 用途 | 必需 |
| --- | --- | --- | --- |
| numpy | >=1.20 | 数值计算 | 是 |
| scipy | >=1.7 | 科学计算 | 是 |
| pandas | >=1.3 | 数据处理 | 是 |
| statsmodels | >=0.13 | 统计建模 | 是 |
| linearmodels | >=4.25 | IV/2SLS估计 | 是 |
| scikit-learn | >=1.0 | 机器学习 | 是 |
| matplotlib | >=3.4 | 可视化 | 可选 |
| dowhy | >=0.9 | 因果推断(备选) | 可选 |

## 5.2 快速安装

```python
# 1. 克隆或解压release包
unzip metamodel_v450_release.zip
cd metamodel/

# 2. 安装依赖
pip install numpy scipy pandas statsmodels linearmodels scikit-learn

# 3. 验证安装
python -c "from metamodel.core.framework import MetaFramework; \
           mf = MetaFramework(); print(f'Verified: {mf.version}')"

# 输出: Verified: 4.5.0-GA
```

## 5.3 验证测试

```python
# 快速验证：导入所有23个适配器
from metamodel.adapters.all_adapters import *
from metamodel.adapters.forecast_adapters import *
from metamodel.adapters.org_personal_adapters import *
from metamodel.adapters.complex_systems_adapters import *
from metamodel.adapters.network_science_adapters import NetworkScienceAdapter
from metamodel.adapters.abm_adapter import ABMAdapter

# 运行六步调用链
from metamodel.core.framework import MetaFramework
mf = MetaFramework()

# 示例：网络分析
from metamodel.adapters.network_science_adapters import NetworkScienceAdapter
net = NetworkScienceAdapter()
result = net(data={
    "network_type": "custom",
    "adjacency": [[0,0.5,0.3],[0.5,0,0.2],[0.3,0.2,0]],
    "analysis_type": "pagerank",
}, params={"damping": 0.85})
print(result["pagerank"])  # [0.42, 0.33, 0.25]

# 示例：临界慢化检测
from metamodel.adapters.complex_systems_adapters import TippingAdapter
tip = TippingAdapter()
result = tip(data={
    "series": list(range(100)),
    "detection_method": "CSD",
}, params={"window_size": 10})
print(result["variance_trend"])
```

> ℹ️ **提示**: **测试通过标准**：所有23个适配器可正常导入和调用，无ImportError。复杂系统适配器（A-16~A-23）通过基础功能测试即可认为安装成功。

============ PART 6 ============
---

# 第六篇 补丁变更日志

## 6.1 v4.3.1补丁变更

**v4.3.1补丁变更清单**

| 类型 | 文件 | 变更内容 |
| --- | --- | --- |
| 新增 | adapters/structural_causal.py | SCMAdapter，实现IV/SEM因果推断 |
| 新增 | adapters/forecast_adapters.py | ForecastAdapter (ARIMA) |
| 新增 | adapters/forecast_adapters.py | BSTSAdapter (贝叶斯时序) |
| 新增 | adapters/forecast_adapters.py | SyntheticControlAdapter (合成控制) |
| 修改 | core/framework.py | 追加upgrade_causal()方法 |
| 修改 | adapters/all_adapters.py | 注册SCMAdapter和预测适配器 |
| 新增 | test_forecast_adapters.py | 预测适配器测试套件 |

## 6.2 v4.4.0补丁变更

**v4.4.0补丁变更清单**

| 类型 | 文件 | 变更内容 |
| --- | --- | --- |
| 新增 | adapters/org_personal_adapters.py | OrganizationAdapter (A-13) |
| 新增 | adapters/org_personal_adapters.py | PersonalGrowthAdapter (A-14) |
| 新增 | adapters/org_personal_adapters.py | TeamManagementAdapter (A-15) |
| 新增 | adapters/org_personal_v2_limit.py | v2极限版适配器(7个增强版) |
| 新增 | test_org_personal.py | 组织/个人/团队测试套件 |

## 6.3 v4.5.0补丁变更

**v4.5.0补丁变更清单**

| 类型 | 文件 | 变更内容 |
| --- | --- | --- |
| 新增 | adapters/complex_systems_adapters.py | TippingAdapter (A-16) 临界慢化检测 |
| 新增 | adapters/complex_systems_adapters.py | SOCAdapter (A-17) 自组织临界性 |
| 新增 | adapters/complex_systems_adapters.py | CausalEmergenceAdapter (A-18) 因果涌现 |
| 新增 | adapters/complex_systems_adapters.py | TransferEntropyAdapter (A-19) 传递熵 |
| 新增 | adapters/complex_systems_adapters.py | EvolutionaryAdapter (A-20) 演化博弈 |
| 新增 | adapters/complex_systems_adapters.py | CoarseGrainingAdapter (A-21) 粗粒化 |
| 新增 | adapters/network_science_adapters.py | NetworkScienceAdapter (A-22) 网络科学 |
| 新增 | adapters/abm_adapter.py | ABMAdapter (A-23) 智能体模拟 |
| 修改 | adapters/all_adapters.py | 注册全部新适配器 |
| 修改 | core/framework.py | 耦合器增强，支持多尺度分析 |
| 修复 | adapters/complex_systems_adapters.py | CausalEmergenceAdapter多维状态输入bug |
| 新增 | test_complex_systems.py | 复杂系统适配器测试套件 |
| 新增 | test_fourth_pole_analysis.py | 中三角第四极分析案例 |

> ⚠️ **注意**: **v4.5.0-GA关键修复**：CausalEmergenceAdapter (A-18) 在v4.5.0-GA中修复了多维micro_states输入时np.unique()报unhashable type的bug。修复方案：新增行向量→标量映射逻辑，通过tuple映射将多维状态转换为离散标量类别。

> ℹ️ **提示**: **兼容性说明**：v4.5.0-GA保持对v4.3.0/v4.4.0的100%向后兼容。所有新增适配器通过独立文件引入，不影响已有API。upgrade_causal()方法在DoWhy不可用时自动降级为统计相关分析，确保环境兼容性。

