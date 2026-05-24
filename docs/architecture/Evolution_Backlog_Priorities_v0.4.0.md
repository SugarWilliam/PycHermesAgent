# Evolution backlog — priorities (personal + team runway)

**Status:** Operational roadmap (engineering) · **Audience:** contributors / sponsors  
**Supersedes nothing:** complements `Phase3_Phase4_Productization_Roadmap_v0.3.0.md` and `Phase3_Phase4_Exit_Checklist_v0.3.0.md`.

**Program tranche one:** engineering priorities here apply through **Phase 4 exit** (roadmap §11). Post–Phase 4 strategic product direction (digital teammate, gateway fork) is chartered in **`Phase5_Evolution_Blueprint_v0.5.0.md`** — update or fork this backlog when Phase 5 is formally opened.

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

## Learning, memory, evolution — stance vs upstream Hermes

This subsection records **product intent** only. It does not prescribe implementation.

### Strategic thesis — controllable, attestable analysis workbench

The maintained thesis is a **controlled, signable, traceable analysis workbench** — not shipping a Hermes-class **autonomous closed-loop learning** product (memory-provider zoo, silent self-rewriting skills, gateway-scale user modeling).

**Do not** chase wholesale adoption of Nous **Hermes Agent** patterns for “self-learning + memory + evolution” as a unified platform goal **during tranche one (through Phase 4 exit)**: cost, boundary risk (chat vs MRAG, MetaHarness invariants), and misalignment with Phase 3→4 exit narratives. **After Phase 4 closure**, any move toward that class of capability must be **re-scoped under `Phase5_Evolution_Blueprint_v0.5.0.md`** with an explicit fork decision (local gateway vs upstream integration), not treated as incremental Phase 3F scope creep.

**Do** prioritise, with high ROI:

- A clear **session / working-memory spine** (carry-over across turns) kept **separate** from MRAG corpora — see `Hermes_Mixed_Integration_Mapping_v0.2.0.md` (memory vs `mrag_core`).
- A **preferences + curation pipeline** for rules/skills so changes are **reviewable and attributable** (Track D / governance).
- **MRAG materialisation** of *approved* knowledge: grounded ingestion, provenance, and citation discipline rather than “everything the model said” in the index.

### Next wave — three high-ROI themes only (no implementation spec)

Owners decompose into ADRs, issues, or exit-checklist rows; this list is **theme-level** by design.

| # | Theme | Outcome (plain language) |
|---|--------|---------------------------|
| **1** | **Session + working memory** | Bounded, auditable continuity across turns **without** folding informal chat into the MRAG knowledge index. |
| **2** | **Preferences + Track D curation** | Precedence, audit trail, and human-governed evolution of rules/skills — changes remain **signable** (who / when / why). |
| **3** | **MRAG materialisation loop** | Low-friction path from accepted outputs or documents into KB chunks that stay **retrieval-grounded** and contract-safe. |

**Weak automation (adjacent, same wave):** derive **candidate skill patches** (e.g. drafts or diffs against `SKILL.md` / policy text) from session or task context — **always** gated by **explicit human review before merge** into any production-activated skill set. **No silent promotion**; Hermes-style autonomy is **out of scope** for this strand unless the product thesis explicitly changes.

---

## Strategic fork (blueprint only) — “digital employee” thesis

This section describes an **optional future direction**. It records **forking options for governance debates** — **not** a committed plan and **no** implementation mandate.

### When this fork applies

If the strategic goal **upgrades** from the current thesis (“**controllable, signable, traceable analysis workbench**”) toward **“always-on personal / team digital employee — knows you better over time”**, the change is **not** a backlog of incremental features alone. Expect:

- A **distinct major-version or product-line** narrative (release governance, naming, compatibility matrix, honest scope docs).
- A **portfolio decision**: whether long-term personalization, multi-session memory, autonomy, and channel surface area are owned **inside this repo** or **delegated**.

### Fork options (evaluation branches — choose later)

| Branch | Idea (high level) | Trade-off sketch (non-exhaustive) |
|--------|-------------------|-------------------------------------|
| **A — Leverage upstream Hermes** | **Operate or integrate Nous Hermes Agent** (`upstream/hermes-agent` / installs) as the **primary runtime** for “digital employee” concerns: gateway platforms, richer memory stacks, cron/delegation patterns, ecosystem scale. **PycHermes**‑class assets (e.g. MetaHarness formal path, MRAG tooling) attach as **sidecar**, library, or **controlled adapter** rather than rewriting that surface. | **Pros:** Faster to “Hermes‑shaped” outcomes; inherits upstream tests and UX depth. **Cons:** Divergence from today’s boundaries (`AGENTS.md`, mixed-integration rules); fusion engineering + dual-runtime ops cost. |
| **B — Deepen PycHermes only** | **Stay on the current codebase** as the chassis and **grow** sessions, preferences, episodic/long-term memory, weak/strong automation, and optional channels — explicitly accepting **overlap** with problems Hermes already solves at scale. | **Pros:** Single stack; aligns with Formal + MRAG‑first narratives. **Cons:** Large sustained investment to approach upstream capability; boundary discipline (memory vs MRAG, MetaHarness) must be maintained or formal exceptions written. |

**Neither branch is selected here.** Selecting one requires stakeholders to approve **risk, compliance (signing / attestations), staffing**, and revisions to **`Phase3_Phase4_Productization_Roadmap`** + **`Hermes_Mixed_Integration_Mapping`** (if integration depth changes materially).

---

## Receipts — what is exercised in CI vs manual (rolling)

| Backlog strand | Receipt (current) |
|----------------|-------------------|
| **P0 Updater feed shape** | **GitHub Actions** `desktop-generic-https-feed-proof`: `desktop/tools/ci_generic_https_feed_proof.cjs` proves `electron-updater` **`GenericProvider`** can fetch and parse **`latest-linux.yml`** from **HTTPS localhost** (self-signed TLS; `NODE_TLS_REJECT_UNAUTHORIZED=0`). **Not covered:** packaged app UX, downloader progress, signatures. |
| **P0 Rules / Track D lineage** | `GET /rules/manifest` **`manifest_version: 2`** + **`runtime_profile`** keyed to `SIDECAR_API_VERSION`; contract test `tests/contract/test_rules_manifest_http.py`. |
| **P1 Evolution backlog receipts (sessions / prefs audit / MRAG materialize / skill drafts)** | Contract module **`tests/contract/test_evolution_roi_receipts.py`**: session scoped **working memory** (prompt injection + JSON persistence); append-only **`preferences.jsonl`** audits; **`POST /knowledge-bases/{id}/materialize`**; **`GET|POST /skills/patch-drafts`** + **`suggest-from-session`** (`DELETE /skills/patch-drafts/{uuid}`); no silent promotion. |
| **P1 Desktop degraded UX** | Top banner **「连接设置」** calls `requestSettingsPanel()` → expands sidebar → opens Settings (sidecar URL / command). Not yet E2E-automated in CI. |

## Quick links

- A2A contract & versioning: [`A2A_SubAgent_Platform_Seam_v0.4.0.md`](./A2A_SubAgent_Platform_Seam_v0.4.0.md)
- Process & longevity: [`Longevity_Stability_and_Team_Process_v0.4.0.md`](./Longevity_Stability_and_Team_Process_v0.4.0.md)
- Windows delivery matrix + updater reproducibility: [`../deployment/Windows_Install_Upgrade_Rollback_Matrix_and_Updater_Proof_v0.4.0.md`](../deployment/Windows_Install_Upgrade_Rollback_Matrix_and_Updater_Proof_v0.4.0.md)
