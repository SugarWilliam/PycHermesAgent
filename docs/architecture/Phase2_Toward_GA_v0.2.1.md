# Phase 2 — 朝向 GA / 生产级 / 商业级（工作草案 v0.2.1）

**状态：** 工作草案（承接 Phase 1 **工程预览已关闭** 的声明；**不** 自动等同于生产就绪）  
**上游文档：** `Phase1_Roadmap_v0.2.0.md` §10、`Execution_Blueprint_v0.2.0.md`、`docs/assessment/Reassessment_v4_FactChecked_and_Upgraded.md`  
**版本锚点：** 发布物从 **`v0.2.1`** 起附带 **Windows 侧车 `pyc-hermes-sidecar.exe`**（见 `.github/workflows/release.yml`）

---

## 1. 目标分层

| 层级 | 含义 | 当前仓库对应动作 |
|------|------|------------------|
| **GA（工程上可以持续发版）** | 可重复构建、签名/哈希可查、门禁清晰、SBOM/audit 纳入节奏 | `release_gates.py` 生产模式、CycloneDX、`npm audit`、迁移备份、Linux desktop `dir+zip` |
| **生产级（生产环境可运维）** | 结构化日志、迁移、备份、降级与锁、发布说明完整 | 侧车文件日志、`migrate --backup-to`、Observability 字段；**仍缺**签名更新器等 |
| **商业级（可对外售卖形态）** | 安装器、合规、渠道分发、支持矩阵 | **未** Claim；需安装器、代码签、隐私与用户协议等（见 `windows-packaging.md`） |

---

## 2. 已落地（相对 Phase 1 关闭时点）

- 生产门禁：`uv lock --check`、`uv export` CycloneDX、MRAG migrate + `--backup-to`、`npm audit`（critical）、Electron Linux **dir + zip**  
- 侧车：轮转日志、`/health` observability 路径、GA optional **`PyInstaller`** import 校验  
- **Release CI**：标签 **`v*.*.*` 推送** 时在 **windows-latest** 上构建 **onefile exe** 并挂到 **GitHub Release**

---

## 3. 建议工作包（按优先级）

1. **P0 — 独立价值验证（Slice 1D）**  
   固定数据集 + 评估脚本 + 报告模板；与 `value_proof` 合同测试 **互补**，不自替代。  

2. **P1 — MRAG 语义与索引**  
   ADR：`docs/design/MRAG_Index_Strategy_Decision_v0.2.0.md` 后续修订；引入 **可选** 神经嵌入路径时保持 **lexical + lock + 迁移** 基线。  

3. **P1 — Windows 侧车 exe 运维**  
   文档：`docs/deployment/Windows_Sidecar_Binary.md`；客户现场：`%LOCALAPPDATA%` / `%APPDATA%` 与 **`--root`** 约定。  

4. **P2 — Desktop 安装器与签名**  
   遵循 `docs/constraints/windows-packaging.md`；Electron + 侧车 **一体** 或 **分离安装** 策略需单独立项。  

5. **P2 — 性能与 E2E**  
   侧车核心路径延迟；最小 E2E（启动→health→一次 KB ingest）。  

---

## 4. 退出标准（草案）

Phase 2 **某一冻结点**若称「Release Candidate」，至少需：

- 本文件 §3 中 **P0 + P1（MRAG ADR 收敛 + exe 运维文档）** 有可指派的 **issue/里程碑**  
- 所有 **tag** 构建在 CI 中 **绿**（含 `release` workflow）  
- `Compatibility_Matrix.md` 与 **发布说明** 同步

---

*Maintainers: 更新本文件时同步 `Execution_Blueprint` 表格中的「Next waves」链接。*
