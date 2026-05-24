# Windows install / upgrade / rollback / downgrade + electron-updater proof

Companion to `Production_Release_Gates.md` Honest scope. This document captures **manual + scripted** proofs until CI has a reproducible HTTPS feed sandbox.

---

## 1. NSIS deterministic smoke (automated baseline)

Already in GitHub Actions: dual-semver PREFIX upgrade harness (`desktop-windows-nsis-silent`). Treat as subset of row **Fresh install → upgrade**.

---

## 2. Manual verification matrix

| Scenario | Preconditions | Steps (high level) | Pass criteria |
|----------|---------------|--------------------|---------------|
| **Fresh install** | Clean `%LOCALAPPDATA%/<App>` subtree | Run latest Setup `/S /D=testprefix` once | Shortcuts/registry per NSIS preset; runtime dirs created |
| **Upgrade (same channel)** | prior semver installed | Run newer Setup silently into same `/D=` | Launch app → about/version matches newer |
| **Uninstall hygiene** | post-install state | Silent uninstall stub | Prefix removed or documented leftovers |
| **Reinstall same version** | after uninstall optional | Silent install identical build | Stable behaviour; no dangling locks |
| **Downgrade attempt** | higher → lower semver | Silent install older over newer | Capture actual NSIS electron-builder semantics; document SUPPORT / BLOCKED |
| **Attach-first sidecar** | mixed misconfigurations | Disconnect sidecar, launch desktop | Visible degraded path (Track A backlog) referencing health endpoint |

Recording: attach logs + PE version probes similar to CI script.

---

## 3. electron-updater repeatable proof skeleton

Desktop already wires `electron-updater` IPC (`desktop/electron/main.js`). `package.json.build.publish.provider=github` placeholders must be overridden for forks.

Checklist:

1. **Prepare two signed or dev builds** differing only by `package.json.version` (+ dist SHA).
2. **Host static YAML** compatible with electron-updater Generic/GitHub Releases layout on an HTTPS reachable origin (Teams may use ephemeral dev certificates + local reverse proxy OR GitHub Releases on a disposable repo matching `owner/repo`).
3. **Point build** (`GH_TOKEN`/`publish` overrides) → run packaged app offline-friendly test: disconnect network except feed host OR use LAN-only mock.
4. **Verify sequence:** `checking → available → downloading → ready` events via `window.updater.onStatus(...)` captures.
5. **Abort / retry resilience:** simulate 404 midway; observe error state surfaced to UI/logs.

Provide automation candidates:

- **`desktop-generic-https-feed-proof` (CI, Ubuntu):** `desktop/tools/ci_generic_https_feed_proof.cjs` — ephemeral OpenSSL TLS + **`latest-linux.yml`** + `electron-updater` **`GenericProvider`**. Validates **publisher feed layout/parsing**, not downloader UI or installer signatures.

- Lightweight Node static server emitting `latest.yml` + zipped artifacts (optional future under `desktop/tools/` for fuller smoke).

Evidence bundle: zipped logs + timestamps + updater feed URLs (redacted tokens).

---

## 4. What remains non-goals until signing exists

Production-grade delta patch validation on signed binaries belongs to secured release infra — document expectations but do **not** block engineering merges on inability to spoof GitHub Releases.
