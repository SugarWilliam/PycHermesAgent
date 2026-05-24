# Phase 3 / Phase 4 退出条件 — 三态对照（相对代码库）

**Status:** Living checklist（随实现更新）  
**Authority:** `docs/architecture/Phase3_Phase4_Productization_Roadmap_v0.3.0.md` §2  
**Last reviewed:** 2026-05-24（Track B web_search 缓存/配额；IPC 业务 MRAG 基准；Track D skill 优先级；可选 dense 嵌入）  

**三态定义**

| 状态 | 含义 |
|------|------|
| **已实现** | 与蓝图退出条件等价的默认路径上已存在可运行实现，并有合同/门禁或明确 API 支撑。 |
| **部分实现** | 有可用的雏形、MVP 或子集；距离「退场条款」的书面要求仍有缺口或未证明。 |
| **未见 / 未达标** | 仓库内无对应实现；或蓝图要求「在基准集上胜出 / 全流程验证」，当前未达到可陈述的结论。 |

> 每项下的「代码依据」为第一手入口；若以测试或 CI 为主要证明，一并注明。

---

## 1. Phase 3 退出条件（Roadmap §2 第一段）

**蓝图原文要义：**桌面连真实 Sidecar（无 mock）· **实时网络与本地 MRAG 检索**工具 + 桌面证据链路 · MRAG 多格式摄取 · 客户加载的 skills/rules 显式审计参与运行时 · **PPT/XLSX 导出级生成** · **混合检索在约定基准集上强于纯词法**。

### 1.1 桌面启动并连接真实本地 Sidecar（无 mock）

| 状态 | 说明 | 代码 / 交付依据 |
|------|------|-----------------|
| **部分实现** | Electron 侧 `sidecarRuntime` attach-first、配置与健康探针已实现；路线图仍要求装机级、干净环境等 **产品化验证**（接近 Track A / Phase 4）。补充：**CI** `desktop-windows-unpacked` + `electron_dist_layout_smoke` 已门禁化 Win 解压布局（非交互安装冒烟）。 | `desktop/electron/sidecarRuntime.js`（及 main/preload）、`desktop/README.md` 启动契约；Sidecar `GET /health`；`.github/workflows/ci.yml` |

### 1.2 实时网络与地面（MRAG）检索作为工具，且在桌面证据流中可见

| 状态 | 说明 | 代码 / 交付依据 |
|------|------|-----------------|
| **已实现（基线）** | **`web_search`** 与 **`knowledge_retrieve`**（调用 `sidecar_api.services.mrag_service` JSON 运行时）均注册于默认 ToolRegistry；工具返回的根级 **`citations[]`** 可被桌面侧 `extractCitationsFromToolContent` 消费。**Formal** 路径将本轮 `tool_results` 汇入 `MetaAnalysisRequest.data_refs` 与 JSON **`analysis_card`**：HTTP 可走 **`http`** 道，`knowledge_retrieve` 归为 **`kb`** 道（仍全程经 `MetaFramework.execute()`）。更强检索 provider、配额 / 观测性、离线缓存等仍为后续（Track B 等）。 | `hermes_engine/web_search.py`、`hermes_engine/knowledge_retrieve_tool.py`、`agent_loop.py`；`sidecar_api/services/chat_service.py`；`desktop/src/services/sidecarClient.js`；`tests/contract/test_web_search.py`、`tests/contract/test_hermes_agent_loop.py` |

### 1.3 MRAG 支持 `text` / `url` / `html` / `pdf` / `docx` / `xlsx` / `pptx` / `image` 摄取

| 格式 | 状态 | 代码 / 交付依据 |
|------|------|-----------------|
| `text` / `markdown` / 泛读文本 | **已实现** | `parse_file_document` 对 `.md` / `.txt` 等 · `mrag_core/parse.py` |
| `html` / `htm` | **已实现（基线）** | ``mrag_core/html_extractor.py``（`<title>` + 跳过 ``script/style/…``，可见正文）· ``parse_file_document`` · ``tests/contract/test_mrag_core.py`` |
| `url` | **已实现** | `ingest_url_text` / `parse_url_document` · `mrag_core/service.py` |
| `pdf` | **已实现** | 专用 PDF 摄取（非 `parse_file` 后缀表）· `mrag_core/pdf_extractor.py`、`sidecar_api/services/mrag_service.py`（`ingest_pdf_document`） |
| `docx` | **已实现（基线）** | `mrag_core/docx_extractor.py` + `parse_file_document` · 路线图承认 heading/table 细粒度仍为后续 |
| `xlsx` | **已实现（基线）** | `mrag_core/xlsx_extractor.py` + `parse_file_document` · 路线图承认 per-cell 引用等为后续 |
| `pptx` | **已实现（基线）** | `pptx_extractor.py`：幻灯片正文 + **`ppt/slides/_rels/slide*.xml.rels`** 解析 `notesSlide` 关系，`Target` 相对于 ``ppt/slides/`` 解析到 ``notesSlides/…``；**`[Notes N]` 的 N 等于 `presentation.xml` 放映序号**，与文件名后缀解耦；`chunk.py` 分块见 `slide-*` / `notes-*` · `tests/contract/test_pptx_extractor_rels.py`、`test_mrag_core.py` |
| `image`（OCR 等） | **已实现（可选）** | `mrag_core/image_extractor.py`（Pillow + pytesseract + 主机 `tesseract`）；缺依赖时报错指引 · `parse_file_document` 常见后缀 · `tests/contract/test_mrag_core.py`（mock OCR） |

**存储侧注记：** 另存在 **SQLite/FTS5** 路径（`mrag_core/sqlite_store.py`、迁移工具），与 JSON `MRAGService` 并行；退出条件按「能力」计，不限定唯一后端。

### 1.4 客户加载的 skills 与 rules 经显式、可审计方式参与运行时

| 状态 | 说明 | 代码 / 交付依据 |
|------|------|-----------------|
| **已实现（基线 + Track D 扩展）** | **Skills：** 继续支持 ``PYC_HERMES_USER_SKILLS_HOME``、运行时 `user_skills`、``.opencode/skills`` 三源合并；“项目”路径仍可按名称覆盖同名单元。新增 **`priority`**（整数，越大越靠前）与 **`overlap_group`**（同组多重激活时在 audit 中产生人工复核 hint）。`sort_skill_names_for_context`/`collect_skill_audit_hints` 将排序与告警写入 ``AgentLoop`` audit（``skill_runtime_audit``）。**Rules：** ``AGENTS.md``/``CLAUDE.md`` discover → prompt 组装路径保持；manifest bundle 增补 ``precedence_explainer`` 说明 ``precedence_order`` 语义。**HTTP：** `GET /rules/manifest`、`POST /skills/user` 等保持不变。**桌面：** Skill/Context UX 仍可继续增强远端同步及可视化编辑器。 | `llm_gateway/skill_metadata.py`、`llm_gateway/skills.py`、`llm_gateway/skill_runtime_audit.py`；`hermes_engine/skill_context.py`、`hermes_engine/agent_loop.py`；`sidecar_api/services/rules_manifest.py`、`skill_service.py`、`user_skill_publish.py` |

### 1.5 基础 **PPT 与 XLSX 生成**（导出产物，非仅摄取）

| 状态 | 说明 | 代码 / 交付依据 |
|------|------|-----------------|
| **已实现（基线）** | `artifact_engine/office_export.py` 生成结构化 ``.xlsx`` / `.pptx`（openpyxl / python-pptx）；`ArtifactEngine.export_bytes` 落盘；HTTP **`POST /artifacts/office`** · `tests/contract/test_sidecar_http.py`。**桌面：** Context 枚举 **`GET /artifacts`**（可按 task 过滤）并由 **`shell:open-path`** 打开落盘文件（`desktopHost.openPath`）；**`/retrieve`** 的目标 KB 可在同面板选择（否则列表首项）。复杂版式（母版、图表、分页打印）仍为后续。 | `artifact_engine/office_export.py`、`sidecar_api/services/office_artifacts.py`、`sidecar_api/http_server.py`；`desktop/src/components/layout/ContextPanel.jsx`、`desktop/electron/main.js`、`desktop/src/services/sidecarClient.js` |

### 1.6 混合检索强于纯词法 — **在已定基准子集上可证明**

| 状态 | 说明 | 代码 / 交付依据 |
|------|------|-----------------|
| **已实现（确定性子集 + IPC 语义对照子集）** | ``lexical`` / ``semantic`` / ``hybrid``：默认 **确定性 trigram** 语义分量；可选安装 **`sentence-transformers`**（`pip install '.[mrag-dense]'`）后通过 ``PYC_HERMES_MRAG_EMBEDDING_BACKEND`` 或 ``RetrievalRequest.embedding_backend`` 启用 **dense** 编码器（缺依赖则回退 trigram 并在 ``RetrievalResult.warnings`` 提示）。Synthetic 基准：``benchmarks/mrag/run_expanded_hybrid_benchmark.py``；**IPC/视频监控语料-shaped** 对照：``benchmarks/mrag/run_ipc_business_hybrid_benchmark.py``（随 `RELEASE_GATES_PRODUCTION=1` 的 ``release_gates.py`` 路径）。Formal 路径 `analysis_card.evidence_chain` 含 **Phase 3F1** 校验；`consistency.py` 另含 **相对时间措辞** 与 **多版本号字面量** 提示（非证明器）。**与路线图「代表性业务基准集全面胜出」**仍可继续加强。 | `mrag_core/retrieve.py`、`mrag_core/embeddings.py`、`mrag_core/embedding_backend.py`；`benchmarks/mrag/run_lexical_hybrid_proof.py`、`benchmarks/mrag/run_expanded_hybrid_benchmark.py`、`benchmarks/mrag/run_ipc_business_hybrid_benchmark.py`；`tests/contract/test_mrag_core.py`、`tests/contract/test_ipc_semantic_benchmark.py`、`tests/contract/test_embedding_backend_contract.py`；`meta_harness/evidence_chain.py`、`meta_harness/consistency.py`；`tests/contract/test_evidence_chain_validation.py` |

---

## 2. Phase 4 退出条件（Roadmap §2 第二段）— 对齐 GA 叙事

**蓝图原文要义：**Windows 打包/升级/更新在干净机验证 · CI 构建并校验 sidecar + 桌面产物 · 门禁覆盖安装不可变、升级、桌面冒烟 · 产品定位为 **RC 级** 而非仅限工程预览。

| 条目 | 状态 | 说明与依据 |
|------|------|------------|
| Windows 打包 / 升级 / 更新器在干净环境验证 | **部分实现** | **GitHub Actions** 已门禁化 **Windows `win-unpacked`** 构建 + **`electron_dist_layout_smoke.py --prefer-unpacked win`**；`desktop/build/icon.ico` 已由 `scripts/write_min_icon_ico.py` 生成入库。真正 **干净机交互安装 / 在线升级 / 回滚矩阵** 仍须人工或专属测试机（非本仓库可单方证伪）。签名与发布渠道见 `Production_Release_Gates.md`。 |
| CI 构建并验证 Python sidecar + 桌面产物 | **已实现（基线）** | `contract-tests`（多版本 Python + MRAG 基准 + 包装探针 + `release_gates.py`）、**`production-gates`**（`RELEASE_GATES_PRODUCTION=1`）、**`desktop-windows-unpacked`**（Windows 解压布局 + audit）共同覆盖；**单个 job 内同时产出 PyInstaller sidecar + 安装包的「同屏一体机」**仍可作加强项。 |
| 门禁覆盖打包、安装不可变、升级、桌面冒烟 | **大部分自动化** | Ubuntu：`release_gates` 含 lockfile、SBOM、MRAG migrate、`dist:dir`、`electron_dist_layout_smoke`；Windows：见上。**代码签名、商店策略、升级通道在线验证**仍为下一层 (`Production_Release_Gates.md` Honest scope)。 |
| 产品可被可信描述为 RC（非仅剩工程预览） | **部分实现（工程侧）** | 自动化与契约已显著收敛到 **「RC 候选工程线」**形态，但 **叙事/法务/签名/渠道** 仍未满足 **GA/商店级** 发布；`README` 仍声明非 production。是否对外称 RC 由发布治理单独决议。 |

---

## 3. 建议的下一轮封闭顺序（仅占位）

1. **Phase 3F（本轮已落地骨干）**：扩展合成基准保持；新增 **IPC/安防语料-shaped** deterministic 对照（``run_ipc_business_hybrid_benchmark.py``）；`consistency.py` 增补 **相对时间** / **semver 字面密度** hint 并汇入 `build_evidence_chain_validation`。**更广义的逻辑证明器 / 全时序消解** 仍为 backlog。  
2. **Track B（本轮已落地骨干）**：`web_search_normalized` / `run_web_search_tool` 可选 ``workspace_root``；**TTL 磁盘缓存**（`cache/web_search`）、**进程内分钟/小时配额**、**失败退避**、**latency_ms / quota / cache_hit** metadata（实现：`hermes_engine/web_search_runtime.py`）。  
3. **Track D（本轮已落地骨干）**：`SKILL.md` front-matter 支持 **`priority`**（整数，用于激活顺序）与 **`overlap_group`**（同组多激活会在 `skill_runtime_audit` / `AgentLoop` audit 提示）；`rules_manifest_bundle` 增加 **`precedence_explainer`**。远端同步 / 可视化仍为后续。  
4. **Dense MRAG（可选垂直）**：`[mrag-dense]` extra + env ``PYC_HERMES_MRAG_EMBEDDING_BACKEND`` / per-request ``RetrievalRequest.embedding_backend``；无依赖时安全回退 **trigram**。  
5. **Phase 4**：Windows 干净机安装 / 升级 / downgrade 与 **electron-updater** 在线证明仍为下一层。

---

## 4. 维护方式

- 本文件 **不替代** Roadmap；Roadmap §2 仍是权威条款文本。  
- 合入影响退出条件的 PR 时，请更新表中 **状态** 与 **依据** 行（或补上 `tests/` / `benchmarks/` 引用）。  
- 若条款与实现有意收敛，应同时修订 `Phase3_Phase4_Productization_Roadmap_v0.3.0.md` 并保留 ADR 或治理纪要链接。
