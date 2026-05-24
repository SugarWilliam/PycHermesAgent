# Phase 3 / Phase 4 退出条件 — 三态对照（相对代码库）

**Status:** Living checklist（随实现更新）  
**Authority:** `docs/architecture/Phase3_Phase4_Productization_Roadmap_v0.3.0.md` §2  
**Last reviewed:** 2026-05-24  

**三态定义**

| 状态 | 含义 |
|------|------|
| **已实现** | 与蓝图退出条件等价的默认路径上已存在可运行实现，并有合同/门禁或明确 API 支撑。 |
| **部分实现** | 有可用的雏形、MVP 或子集；距离「退场条款」的书面要求仍有缺口或未证明。 |
| **未见 / 未达标** | 仓库内无对应实现；或蓝图要求「在基准集上胜出 / 全流程验证」，当前未达到可陈述的结论。 |

> 每项下的「代码依据」为第一手入口；若以测试或 CI 为主要证明，一并注明。

---

## 1. Phase 3 退出条件（Roadmap §2 第一段）

**蓝图原文要义：**桌面连真实 Sidecar（无 mock）· 实时网络检索工具 + 桌面证据链路 · MRAG 多格式摄取 · 客户加载的 skills/rules 显式审计参与运行时 · **PPT/XLSX 导出级生成** · **混合检索在约定基准集上强于纯词法**。

### 1.1 桌面启动并连接真实本地 Sidecar（无 mock）

| 状态 | 说明 | 代码 / 交付依据 |
|------|------|-----------------|
| **部分实现** | Electron 侧 `sidecarRuntime` attach-first、配置与健康探针已实现；路线图仍要求装机级、干净环境等 **产品化验证**（接近 Track A / Phase 4）。 | `desktop/electron/sidecarRuntime.js`（及 main/preload）、`desktop/README.md` 启动契约；Sidecar `GET /health` |

### 1.2 实时网络检索作为工具，且在桌面证据流中可见

| 状态 | 说明 | 代码 / 交付依据 |
|------|------|-----------------|
| **部分实现** | `web_search` 已注册于默认 ToolRegistry，返回 `citations[]`；桌面 `extractCitationsFromToolContent` 消费根级 `citations`。路由图 **B5（Formal 消费网络证据不绕开 MetaFramework）**、更强 provider 等仍属缺口。 | `src/pyc_hermes_agent/hermes_engine/web_search.py`、`agent_loop.py`；`desktop/src/services/sidecarClient.js`；`tests/contract/test_web_search.py` |

### 1.3 MRAG 支持 `text` / `url` / `html` / `pdf` / `docx` / `xlsx` / `pptx` / `image` 摄取

| 格式 | 状态 | 代码 / 交付依据 |
|------|------|-----------------|
| `text` / `markdown` / 泛读文本 | **已实现** | `parse_file_document` 对 `.md` / `.txt` 等 · `mrag_core/parse.py` |
| `html` / `htm` | **已实现** | `parse_file_document` 映射 `source_type="html"` · `mrag_core/parse.py` |
| `url` | **已实现** | `ingest_url_text` / `parse_url_document` · `mrag_core/service.py` |
| `pdf` | **已实现** | 专用 PDF 摄取（非 `parse_file` 后缀表）· `mrag_core/pdf_extractor.py`、`sidecar_api/services/mrag_service.py`（`ingest_pdf_document`） |
| `docx` | **已实现（基线）** | `mrag_core/docx_extractor.py` + `parse_file_document` · 路线图承认 heading/table 细粒度仍为后续 |
| `xlsx` | **已实现（基线）** | `mrag_core/xlsx_extractor.py` + `parse_file_document` · 路线图承认 per-cell 引用等为后续 |
| `pptx` | **未见** | `src/` 下无 `pptx` 摄取路径；`parse.py` 无 `.pptx` 分支 |
| `image`（OCR 等） | **未见** | `mrag_core` 无 image/OCR 摄取实现 |

**存储侧注记：** 另存在 **SQLite/FTS5** 路径（`mrag_core/sqlite_store.py`、迁移工具），与 JSON `MRAGService` 并行；退出条件按「能力」计，不限定唯一后端。

### 1.4 客户加载的 skills 与 rules 经显式、可审计方式参与运行时

| 状态 | 说明 | 代码 / 交付依据 |
|------|------|-----------------|
| **部分实现** | **Skills：** 内置技能可激活并进入 `AgentLoop`；项目下 `.opencode/skills` 可走发现/列表，与 Track D「用户目录 / 审计 / 规则优先级全面模型」仍有距离。**Rules：** `llm_gateway.rules` 可做文件发现；**未见**与 `AgentLoop` 系统拼装强绑定的确定性优先级管道（路线图 D4）。 | `skill_service.py`、`hermes_engine/skill_context.py`、`llm_gateway/skills.py`、`llm_gateway/rules.py` |

### 1.5 基础 **PPT 与 XLSX 生成**（导出产物，非仅摄取）

| 状态 | 说明 | 代码 / 交付依据 |
|------|------|-----------------|
| **部分实现** | **通用产物落盘与列举**（`ArtifactEngine`、HTTP `/artifacts`）存在；路线图 Track E 所指的 **结构化 PPTX / XLSX 生成 MVP**（幻灯片与工作表语义）**未见**专用生成器。 | `src/pyc_hermes_agent/artifact_engine/__init__.py`、`sidecar_api/http_server.py` |

### 1.6 混合检索强于纯词法 — **在已定基准子集上可证明**

| 状态 | 说明 | 代码 / 交付依据 |
|------|------|-----------------|
| **未达标** | 已实现 `lexical` / `semantic`（字符 trigram 向量）/ `hybrid` 及权重 · **无**路线图所要求的「在代表性子集上的对比基准 + hybrid 胜出」闭环 | `mrag_core/retrieve.py`、`mrag_core/embeddings.py`、`contracts/schemas.py`（`RetrievalRequest`）；`benchmarks/` 现有为 **MetaHarness 15-case**，**非** MRAG hybrid vs lexical |

---

## 2. Phase 4 退出条件（Roadmap §2 第二段）— 对齐 GA 叙事

**蓝图原文要义：**Windows 打包/升级/更新在干净机验证 · CI 构建并校验 sidecar + 桌面产物 · 门禁覆盖安装不可变、升级、桌面冒烟 · 产品定位为 **RC 级** 而非仅限工程预览。

| 条目 | 状态 | 说明与依据 |
|------|------|------------|
| Windows 打包 / 升级 / 更新器在干净环境验证 | **部分实现** | CI 已有 `desktop-windows-unpacked`（`dist:win-unpacked`）；**升级器与干净机长验**仍以文档/人工为主，见 `Production_Release_Gates.md`「Honest scope」 |
| CI 构建并验证 Python sidecar + 桌面产物 | **部分实现** | Ubuntu：`contract-tests` + `production-gates`（含桌面 `dist:dir`）；Windows：`desktop-windows-unpacked`；与「全流程 sidecar 安装包同上屏验证」可作加强 |
| 门禁覆盖打包、安装不可变、升级、桌面冒烟 | **部分实现** | `scripts/release_gates.py`、`pyc-hermes-packaging-probe`、SBOM、`npm audit` 等已接；**签名、更新频道、装机矩阵**明示为下一层 (`Production_Release_Gates.md`) |
| 产品可被可信描述为 RC（非仅剩工程预览） | **未见** | 需 Phase 3 未闭合项 + Phase 4 验证与发布叙事共同到位；`AGENTS.md` 仍以 Phase 1/2 「非 production」为约束表述 |

---

## 3. 建议的下一轮封闭顺序（仅占位）

1. 补齐蓝图 **硬性清单缺口**：`pptx` / `image` 摄取 **或** 调整路线图退出条件措辞（若范围收缩需走治理文档）。  
2. **Artifact Track E**：PPTX/XLSX **生成** MVP，与现有 `ArtifactEngine` 衔接。  
3. **MRAG 混合检索**：新增 `benchmarks/mrag/`（或等价）与 CI/门禁挂钩，满足「hybrid > lexical on subset」。  
4. **Track D**：rules 拼装顺序 + 用户 skill 加载与审计字段。  
5. **Phase 4**：干净 Windows 安装与升级/downgrade 用例门禁化。

---

## 4. 维护方式

- 本文件 **不替代** Roadmap；Roadmap §2 仍是权威条款文本。  
- 合入影响退出条件的 PR 时，请更新表中 **状态** 与 **依据** 行（或补上 `tests/` / `benchmarks/` 引用）。  
- 若条款与实现有意收敛，应同时修订 `Phase3_Phase4_Productization_Roadmap_v0.3.0.md` 并保留 ADR 或治理纪要链接。
