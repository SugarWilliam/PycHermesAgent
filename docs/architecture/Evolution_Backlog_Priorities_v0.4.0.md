# Evolution backlog — priorities (personal + team runway)

**Status:** Operational roadmap (engineering) · **Audience:** contributors / sponsors  
**Supersedes nothing:** complements `Phase3_Phase4_Productization_Roadmap_v0.3.0.md` and `Phase3_Phase4_Exit_Checklist_v0.3.0.md`.

---

## Purpose

Provide a single **prioritised backlog** aligning:

1. **Intelligence depth** — Phase 3F “hard” cognition (non-provers, causal hygiene, timelines).
2. **Track D maturity** — skills/rules ecosystem (distribution, precedence UX, moderation).
3. **MRAG quality** — dense embeddings, citations, benchmarking on your real corpora (redacted bundles).
4. **Track A product feel** — attach-first UX, degraded states, safe defaults.
5. **A2A / sub-agents seam** — versioned facade only today (`contracts/a2a.py`, `GET /capabilities/a2a`); federation later.
6. **Installer + updater proofs** — see `docs/deployment/Windows_Install_Upgrade_Rollback_Matrix_and_Updater_Proof_v0.4.0.md`.
7. **Operational longevity** — see `docs/architecture/Longevity_Stability_and_Team_Process_v0.4.0.md`.

---

## Priority tiers (recommended execution order)

| Tier | Horizon | Themes |
|------|---------|--------|
| **P0 Reliability shell** | 1–2 sprints | Formalise Windows install/update/rollback manual matrix + scripted pieces; deterministic updater feed smoke checklist; widen contract tests touching sidecar + MRAG migration; pin electron-updater GH owner/repo or override via env documented. |
| **P1 Product truth** | 2–4 sprints | Track A degraded UX backlog (timeouts, unreachable sidecar banners, remediation links); Electron IPC tests for updater status surface; nightly MRAG regressions optional job. |
| **P2 Intelligence & governance** | rolling | Extend Phase 3F heuristics (numeric/percent conflicts, modality-specific hints); deepen rules precedence tooling; skill publishing review workflow drafts. |
| **P3 A2A / federation** | after P0–P2 | Negotiate transports (mTLS), add POST `/a2a/*` stubs with audit, ship threat model ADR before enabling network peers. |

Each tier should end with **documented receipts** (test names, checklist rows, screenshots for desktop-only regressions).

---

## Receipts — what is exercised in CI vs manual (rolling)

| Backlog strand | Receipt (current) |
|----------------|-------------------|
| **P0 Updater feed shape** | **GitHub Actions** `desktop-generic-https-feed-proof`: `desktop/tools/ci_generic_https_feed_proof.cjs` proves `electron-updater` **`GenericProvider`** can fetch and parse **`latest-linux.yml`** from **HTTPS localhost** (self-signed TLS; `NODE_TLS_REJECT_UNAUTHORIZED=0`). **Not covered:** packaged app UX, downloader progress, signatures. |
| **P0 Rules / Track D lineage** | `GET /rules/manifest` **`manifest_version: 2`** + **`runtime_profile`** keyed to `SIDECAR_API_VERSION`; contract test `tests/contract/test_rules_manifest_http.py`. |
| **P1 Desktop degraded UX** | Top banner **「连接设置」** calls `requestSettingsPanel()` → expands sidebar → opens Settings (sidecar URL / command). Not yet E2E-automated in CI. |

## Quick links

- A2A contract & versioning: [`A2A_SubAgent_Platform_Seam_v0.4.0.md`](./A2A_SubAgent_Platform_Seam_v0.4.0.md)
- Process & longevity: [`Longevity_Stability_and_Team_Process_v0.4.0.md`](./Longevity_Stability_and_Team_Process_v0.4.0.md)
- Windows delivery matrix + updater reproducibility: [`../deployment/Windows_Install_Upgrade_Rollback_Matrix_and_Updater_Proof_v0.4.0.md`](../deployment/Windows_Install_Upgrade_Rollback_Matrix_and_Updater_Proof_v0.4.0.md)
