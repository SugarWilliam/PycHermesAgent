# Longevity, stability & team operating model

Goal: sustain **individual power users + small engineering teams** on PycHermesAgent without regressing architectural boundaries declared in `AGENTS.md`.

---

## Engineering invariants

1. **Contracts first:** any behavioural change impacting HTTP/SSE payloads → update `contracts/` + add / extend **`tests/contract`** before merge.
2. **Release gates pyramid:** lint/type → contract → integration (sparse) → manual desktop proofs logged in checklist docs.
3. **Backward compatibility budgets:** MRAG manifest / index bumps require **`pyc-hermes-mrag-migrate` plan** artefacts in PR description when touching persistence.
4. **Dependency hygiene:** `uv.lock` is authoritative; introducing heavy ML stacks (sentence-transformers) stays optional extras (`mrag-dense`).

---

## Operational rhythm

| Cadence | Action |
|---------|--------|
| Per PR | `./scripts/release_gates.py` (or CI equivalent) passes; hyperlink benchmark commands if retrieval touched |
| Monthly | rerun **Windows smoke matrix** slices (fresh install subset at minimum); export logs to shared drive/issue |
| Quarterly | reconcile `Phase3_Phase4_Exit_Checklist_*` statuses + Compatibility Matrix deltas |

---

## Evolution standards

- **Semantic versioning (`app_version`):** MINOR bump signals user-visible behavioural contract changes; PATCH for fixes/docs-only if release notes say so.
- **Feature flags:** long-running risky areas (dense embeddings, A2A POST) stay behind explicit env knobs until GA narrative approves.

---

## When to escalate to ADR form

Dual implementations, persistence migrations, federation/trust crossing process boundaries → short ADR in `docs/design/` with rationale + supersession pointer.
