# A2A / SubAgent platform seam (reserved)

## Status

**Implemented today:** declarative **`GET /capabilities/a2a`** JSON (built from `pyc_hermes_agent.contracts.a2a`).  
**Not implemented:** networked peer negotiation, delegated tool loops beyond `hermes_engine`, mutual TLS transports.

Naming: we use **“sub-agent handoff envelope”** to mean a future opaque-but-auditable JSON payload describing work another agent persona/runtime may continue. This is orthogonal to Electron “child windows” — A2A is an **integration plane**, not a UI concept.

---

## Non-negotiables (inherits `AGENTS.md`)

- Formal analysis endpoints continue to funnel through **`MetaFramework.execute()`** — A2A must not carve a shortcut.
- **Provider/SDK objects remain inside `llm_gateway`** — peer payloads are JSON-only.
- **MRAG retains storage boundaries** — peer agents ingest through public MRAG APIs, not filesystem peeks inside another machine without policy.

---

## Versioning axes

| Field | Meaning |
|-------|---------|
| `a2a_protocol_id` | Namespace for this organization's A2A dialect (`pyc-hermes-a2a`). |
| `a2a_protocol_version` | SemVer for the advertisement JSON **only** (`contracts/a2a.py`). Bump when keys change or deprecate.

---

## Roadmap checkpoints

1. **v0.1 (current)** — static capability advertisement + prose ADR linkage.
2. **v0.2** — `POST /a2a/handoff/reserve` stub returning `501 HANDOFF_RESERVED` but validating JSON schema(s).
3. **v0.3** — opt-in enqueue with policy gate + audit ledger (local SQLite or append-only journal under `%LOCALAPPDATA%`).
4. **v0.4+** — optional mutual TLS federation & peer registry (out-of-repo infrastructure).

ADR requirement: introduce `docs/design/ADR_A2A_MinimalDelegation_v0.x.md` before enabling networked POST routes.
