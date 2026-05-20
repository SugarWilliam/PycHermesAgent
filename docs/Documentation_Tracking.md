# Documentation tracking / 文档跟踪

**Purpose:** Maintain a single inventory for `docs/` so additions, moves, or major revisions are traceable alongside code changes.

**Anchors:**
- Governance: [`Project_Development_and_Release_Governance.md`](./Project_Development_and_Release_Governance.md)
- Product execution spine: [`architecture/Phase3_Phase4_Productization_Roadmap_v0.3.0.md`](./architecture/Phase3_Phase4_Productization_Roadmap_v0.3.0.md) (Phase 3–4 umbrella)
- Release notes stubs: [`releases/README.md`](./releases/README.md)

**Maintenance (约定):**

1. Add or relocate a Markdown file under `docs/` → update the tables below (or the path list in §4) in the same PR/commit whenever practical.
2. Tag-driven user-facing deltas → mirror summary in [`releases/`](./releases/) and, when API/contract drift occurs, bump [`architecture/Compatibility_Matrix.md`](./architecture/Compatibility_Matrix.md).

---

## 1. Phase 3–4 roadmap cluster (v0.3.0 line)

Plan documents underpinning **`Phase3_Phase4_Productization_Roadmap_v0.3.0.md`**.

| ID | Document | Topic |
|----|----------|--------|
| 3 umbrella | [`architecture/Phase3_Phase4_Productization_Roadmap_v0.3.0.md`](./architecture/Phase3_Phase4_Productization_Roadmap_v0.3.0.md) | Phase 3 → 4 productization outline |
| 3A | [`architecture/Phase3A_Desktop_Integration_Plan_v0.3.0.md`](./architecture/Phase3A_Desktop_Integration_Plan_v0.3.0.md) | Desktop ↔ sidecar integration |
| 3B | [`architecture/Phase3B_Network_Search_Plan_v0.3.0.md`](./architecture/Phase3B_Network_Search_Plan_v0.3.0.md) | Network / search grounding |
| 3C | [`architecture/Phase3C_Multiformat_MRAG_Plan_v0.3.0.md`](./architecture/Phase3C_Multiformat_MRAG_Plan_v0.3.0.md) | Multiformat MRAG |
| 3D | [`architecture/Phase3D_Skills_Rules_Runtime_Plan_v0.3.0.md`](./architecture/Phase3D_Skills_Rules_Runtime_Plan_v0.3.0.md) | Skills + rules runtime umbrella |
| 3D1 | [`architecture/Phase3D1_Dynamic_Skill_Authoring_Plan_v0.3.0.md`](./architecture/Phase3D1_Dynamic_Skill_Authoring_Plan_v0.3.0.md) | Dynamic skill authoring |
| 3D2 | [`architecture/Phase3D2_Rules_Runtime_Assembly_Plan_v0.3.0.md`](./architecture/Phase3D2_Rules_Runtime_Assembly_Plan_v0.3.0.md) | Rules assembly / runtime |
| 3E | [`architecture/Phase3E_PPT_XLSX_Authoring_Plan_v0.3.0.md`](./architecture/Phase3E_PPT_XLSX_Authoring_Plan_v0.3.0.md) | PPT / XLSX authoring umbrella |
| 3E1 | [`architecture/Phase3E1_PPT_Authoring_Plan_v0.3.0.md`](./architecture/Phase3E1_PPT_Authoring_Plan_v0.3.0.md) | PPT authoring |
| 3E2 | [`architecture/Phase3E2_XLSX_Authoring_Plan_v0.3.0.md`](./architecture/Phase3E2_XLSX_Authoring_Plan_v0.3.0.md) | XLSX authoring |
| 3F | [`architecture/Phase3F_Retrieval_MetaFramework_Strengthening_Plan_v0.3.0.md`](./architecture/Phase3F_Retrieval_MetaFramework_Strengthening_Plan_v0.3.0.md) | Retrieval & MetaHarness strengthening |
| 3F1 | [`architecture/Phase3F1_Evidence_Chain_Validation_Plan_v0.3.0.md`](./architecture/Phase3F1_Evidence_Chain_Validation_Plan_v0.3.0.md) | Evidence chain validation |
| 3G | [`architecture/Phase3G_Windows_Release_Hardening_Plan_v0.3.0.md`](./architecture/Phase3G_Windows_Release_Hardening_Plan_v0.3.0.md) | Windows release hardening |
| 3G1 | [`architecture/Phase3G1_Windows_Installer_Updater_Plan_v0.3.0.md`](./architecture/Phase3G1_Windows_Installer_Updater_Plan_v0.3.0.md) | Installer / updater |

---

## 2. Architecture baseline (historical anchors)

| Document | Role |
|----------|------|
| [`architecture/PycHermesAgent_Architecture_v0.2.0.md`](./architecture/PycHermesAgent_Architecture_v0.2.0.md) | High-level architecture |
| [`architecture/PycHermesAgent_Solution_Architecture_v0.2.0.md`](./architecture/PycHermesAgent_Solution_Architecture_v0.2.0.md) | Solution architecture |
| [`architecture/Execution_Blueprint_v0.2.0.md`](./architecture/Execution_Blueprint_v0.2.0.md) | Execution blueprint |
| [`architecture/Phase0_Blueprint_v0.2.0.md`](./architecture/Phase0_Blueprint_v0.2.0.md) | Phase 0 |
| [`architecture/Phase1_Roadmap_v0.2.0.md`](./architecture/Phase1_Roadmap_v0.2.0.md) | Phase 1 roadmap (closed EP) |
| [`architecture/Phase2_Toward_GA_v0.2.1.md`](./architecture/Phase2_Toward_GA_v0.2.1.md) | Phase 2 toward GA draft |
| [`architecture/Hermes_Mixed_Integration_Mapping_v0.2.0.md`](./architecture/Hermes_Mixed_Integration_Mapping_v0.2.0.md) | Hermes integration mapping |
| [`architecture/Compatibility_Matrix.md`](./architecture/Compatibility_Matrix.md) | Compatibility / contracts |

---

## 3. Other `docs/` areas

| Area | Contents |
|------|----------|
| **Assessment** | [`assessment/Reassessment_v4_FactChecked_and_Upgraded.md`](./assessment/Reassessment_v4_FactChecked_and_Upgraded.md) |
| **Constraints** | `constraints/*.md` (MetaHarness / MRAG / OpenCode / Windows packaging) |
| **Deployment** | `deployment/*.md` (gates, usage, Windows sidecar) |
| **Design / ADRs** | `design/*.md` |
| **Features** | [`features/PycHermesAgent_Feature_Details_v0.2.0.md`](./features/PycHermesAgent_Feature_Details_v0.2.0.md) |
| **Releases** | `releases/v0.2.1.md`, `releases/v0.3.0.md`, [`releases/preview_draft.md`](./releases/preview_draft.md) |
| **Superpowers** | `superpowers/specs/*.md`, `superpowers/plans/*.md` |
| **Project root (docs)** | [`Project_Development_and_Release_Governance.md`](./Project_Development_and_Release_Governance.md), [`PycHermesAgent_Evaluation_Report_v1.0.md`](./PycHermesAgent_Evaluation_Report_v1.0.md), [`Development_Checkpoint_2026-05-18.md`](./Development_Checkpoint_2026-05-18.md) |

---

## 4. Full Markdown manifest (automatable)

Canonical path set (glob: `docs/**/*.md`):

- `architecture/Compatibility_Matrix.md`
- `architecture/Execution_Blueprint_v0.2.0.md`
- `architecture/Hermes_Mixed_Integration_Mapping_v0.2.0.md`
- `architecture/Phase0_Blueprint_v0.2.0.md`
- `architecture/Phase1_Roadmap_v0.2.0.md`
- `architecture/Phase2_Toward_GA_v0.2.1.md`
- `architecture/Phase3_Phase4_Productization_Roadmap_v0.3.0.md`
- `architecture/Phase3A_Desktop_Integration_Plan_v0.3.0.md`
- `architecture/Phase3B_Network_Search_Plan_v0.3.0.md`
- `architecture/Phase3C_Multiformat_MRAG_Plan_v0.3.0.md`
- `architecture/Phase3D1_Dynamic_Skill_Authoring_Plan_v0.3.0.md`
- `architecture/Phase3D2_Rules_Runtime_Assembly_Plan_v0.3.0.md`
- `architecture/Phase3D_Skills_Rules_Runtime_Plan_v0.3.0.md`
- `architecture/Phase3E1_PPT_Authoring_Plan_v0.3.0.md`
- `architecture/Phase3E2_XLSX_Authoring_Plan_v0.3.0.md`
- `architecture/Phase3E_PPT_XLSX_Authoring_Plan_v0.3.0.md`
- `architecture/Phase3F1_Evidence_Chain_Validation_Plan_v0.3.0.md`
- `architecture/Phase3F_Retrieval_MetaFramework_Strengthening_Plan_v0.3.0.md`
- `architecture/Phase3G1_Windows_Installer_Updater_Plan_v0.3.0.md`
- `architecture/Phase3G_Windows_Release_Hardening_Plan_v0.3.0.md`
- `architecture/PycHermesAgent_Architecture_v0.2.0.md`
- `architecture/PycHermesAgent_Solution_Architecture_v0.2.0.md`
- `assessment/Reassessment_v4_FactChecked_and_Upgraded.md`
- `constraints/meta-harness-boundaries.md`
- `constraints/mrag-evidence-boundaries.md`
- `constraints/opencode-compatibility.md`
- `constraints/windows-packaging.md`
- `deployment/Production_Release_Gates.md`
- `deployment/PycHermesAgent_Usage_Deployment_Guide_v0.2.0.md`
- `deployment/Windows_Sidecar_Binary.md`
- `design/ADR_Skill_Runtime_Permissions_Phase1_v0.2.0.md`
- `design/Asset_Promotion_Strategy_v0.2.0.md`
- `design/MRAG_Index_Strategy_Decision_v0.2.0.md`
- `design/PycHermesAgent_Detailed_Design_v0.2.0.md`
- `Development_Checkpoint_2026-05-18.md`
- `Documentation_Tracking.md` *(this file)*
- `features/PycHermesAgent_Feature_Details_v0.2.0.md`
- `Project_Development_and_Release_Governance.md`
- `PycHermesAgent_Evaluation_Report_v1.0.md`
- `releases/preview_draft.md`
- `releases/README.md`
- `releases/v0.2.1.md`
- `releases/v0.3.0.md`
- `superpowers/plans/2026-05-20-phase3-p0-foundation-calibration.md`
- `superpowers/specs/2026-05-20-phase3-rollout-design.md`
- `superpowers/specs/2026-05-21-phase3a-a1-sidecar-startup-design.md`
