# PycHermesAgent 全量再评估总结（v4.0）— **事实校对与升级稿**

**文档状态：** 在 v4.0 复盘报告基础上，经 **GitHub 仓库源码逐条核对** 后的修订版；原报告中与代码不符处已更正，属实结论保留并 **上收为可执行路线图引用**。  
**校对基准：** `main` 分支（含 Phase 1 关闭后的生产门禁、SBOM、桌面 Linux 打包等提交）；**非**「32 个 commit 冻结快照」的文学化计数。  
**修订日期：** 2026-05-26（持续随仓库更新）

---

## 1. 原报告结论：哪些属实

以下论断与当前 **`src/pyc_hermes_agent`** 一致，**可作为架构与产品的可信描述**：

| 主题 | 属实要点（源码锚点） |
|------|----------------------|
| **MetaHarness 路由** | `MethodRoutingPolicy`（`meta_harness/router/policy.py`）：`builtin()` 关键词表、`with_request_overlay` / `with_overlay`、`DataShapeRule`、请求级 `meta_routing` 覆盖（含 `keyword_boosts`、`data_shape_bonus`、`data_shape_rules`、标量调参）。 |
| **方法钉扎** | **`routing_pin_method_id`** 为 **模块级函数**，从 `request.meta_routing` 读取 `pin_method` / `forced_method`，返回 **`str | None`**（见 `policy.py`）。**并非** 类方法、也 **不** 返回 `float` 分数。 |
| **SR 分级策略** | `SrGradingPolicy`（`meta_harness/quality/sr_grade.py`）：`target_sr_grade` 覆盖、`degraded` / `selected is None` / overclaim 语言 / 执行细节映射 **SR-C1/SR-C2**。CE/SR 在职责上与 CE 能力描述分离。 |
| **Overclaim 检测** | `OVERCLAIM_PHRASES` 与 `request_has_overclaim_language` 在 **`meta_harness/quality/checks.py`**（**不是** 文件名 `checker.py`）。**共 7 条英文+中文短语**，具体词条 **以源码为准**（见该文件元组）。 |
| **MRAG Hybrid** | `mrag_core/retrieve.py`：`lexical` / `semantic` / `hybrid`，`semantic_weight` 裁剪到 \[0,1\]，hybrid 为 lexical 与 trigram 语义的凸组合；**语义向量**为 **`character_trigram_embedding`** + 余弦相似度。 |
| **Trigram 嵌入** | `mrag_core/embeddings.py`：字符 trigram → **每个 trigram 的 BLAKE2b（8 字节摘要）定桶** → **固定维度直方图** → L2 归一化；**不是**「整段文本单次 `blake2b(digest_size=32)` 再与 histogram 简单拼接」那种实现。 |
| **工程工具链** | Ruff（E/W+F）、mypy、**`uv` + `uv.lock`**、CI 中 `release_gates.py`：**属实**。 |
| **Skill 与 AgentLoop** | 无名为 `audit` 的独立子系统；**属实行为**为：`start` 事件中 **`activated_skills` + `skills_runtime_policy`**（与 Phase 1 ADR 一致的可审计载荷）；未知 skill 在 **`build_skill_context_messages`** 中 **`ValueError`**。路线图用语建议用 **「可审计载荷」** 而非泛泛 **「audit 管线」**。 |
| **测试布局** | `tests/contract` 下 **约 25 个** `test_*.py` 量级（随增减变化），**不宜** 写死「27 个文件」作为硬指标。 |

---

## 2. 原报告中应废弃或必须改正的表述

1. **`SrGradingPolicy.grade(...)` 伪代码参数**：源码为 `grade(self, request, selected, degraded, execution_details)`，overclaim 由 **`request_has_overclaim_language(request)`** 推断，**无** `overclaim: bool` 形参。  
2. **`routing_pin_method_id(self, method_id) -> float`**：全系 **错误**；见上表。  
3. **Overclaim 短语枚举**（如 guaranteed / 绝对保证等）：与仓库 **不一致**；**唯一权威列表**在 `checks.py`。  
4. **`mypy strict / 生产级严格`**：当前 **`pyproject.toml`** 为 `ignore_missing_imports = true` 等，**属于务实配置**，**不等价**于 mypy **strict**。  
5. **`meta_harness/quality/checker.py`**：**应** 改为 **`checks.py`**。  
6. **「仅 4 个 commit / 32-commit 封版」**：仓库在 Phase 1 关闭之后仍有 **生产门禁、SBOM、桌面、PyInstaller 准备等** 提交；评估应 **以 tag/文档日期 + `git log` 为准**，避免叙事化 commit 数。  
7. **综合百分比 / A-/B+ 等**：可作 **内部雷达图语言**，**不可**当作对外或问责 KPI，除非配套 **可复现实验协议**（见下节「升级」）。

---

## 3. 升级纳入：从「评估」到「路线图」

以下内容在原报告中**方向正确**，本稿 **正式纳入** 为与 **`AGENTS.md`、Phase 1 路线图、Execution Blueprint** 一致的后续工作包（细节见 **`docs/architecture/Phase2_Toward_GA_v0.2.1.md`**）：

1. **Slice 1D / 独立验证**：在保留 `value_proof` 合同测试的前提下，规划 **外部或可复现基准**；避免方法论价值 **仅自证**。  
2. **MRAG 向量化**：trigram 为 **local-first、确定性** 过渡；Phase 2+ **嵌入/重排/索引策略** 需 **ADR**（与 `Execution_Blueprint` 工作流 2 对齐）。  
3. **供给链与发布物**：SBOM（CycloneDX）、lockfile、**Windows 侧车 onefile exe**（CI 构建并随 **GitHub Release** 投递）——与 **商业/生产交付** 对齐。  
4. **覆盖率 / 性能 / E2E**：按 `AGENTS.md` 测试优先级 **分期** 引入，不一次性虚名堆砌。  
5. **文档诚实性**：继续区分 **Engineering preview** / **Release candidate** / **Production**；禁止把预测输出写成交付级因果断言（项目规则不变）。

---

## 4. 如何使用本稿

- **对外技术沟通**：仅引用 **§1 属实表 + §2 改正清单**；评分百分比建议不出正式对外材料。  
- **内部规划**：以 **§3** 为输入，更新 Phase 2 里程碑与 CI/Release 检查项。  
- **再版评估**：下一个冻结点建议 **`v0.2.1` tag**（或更高）+ **自动生成 `git log` 节选** + **本文件 diff**。

---

## 5. 附录：原 v4.0 叙事中仍值得保留的「判断型」结论（非源码可证）

- **方法论层空心化 / 占位执行张力**：仍为 **策略风险**，需靠 **独立基准 + 真分析管线** 缓解。  
- **Desktop / Markdown 渲染 / 多模态**：与当前仓库 **范围诚实** 一致——多数仍 **未**  Claim 生产完成。  
- **Trigram 与神经编码器的代差**：**技术判断成立**，与实现注释（hybrid 警告语）一致。

---

*本文件取代「仅叙事、未核对源码」的 v4.0 外发版本作为仓库内权威复盘；若外部仍有旧 PDF/Markdown，请以本路径为准。*
