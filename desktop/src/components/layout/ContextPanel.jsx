import { useEffect, useState, useCallback } from 'react'
import useChatStore from '../../store/chatStore'
import useUiStore from '../../store/uiStore'
import { useSidecarStatusStore } from '../../store/sidecarStatusStore'
import { fetchArtifacts, fetchPreferences, fetchRules, fetchRulesManifest, listKnowledgeBases } from '../../services/sidecarClient'
import CitationList from '../context/CitationList'

export default function ContextPanel() {
  const contextData = useUiStore((s) => s.contextData)
  const toggleContextPanel = useUiStore((s) => s.toggleContextPanel)
  const conversations = useChatStore((s) => s.conversations)
  const activeConversationId = useChatStore((s) => s.activeConversationId)

  // Get the latest assistant message for live metadata
  const activeConv = conversations.find((c) => c.id === activeConversationId)
  const assistantMsgs = (activeConv?.messages || []).filter((m) => m.role === 'assistant')
  const lastAssistant = assistantMsgs[assistantMsgs.length - 1]

  return (
    <div className="flex flex-col h-full w-80 bg-white dark:bg-gray-900 p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
          Context
        </span>
        <button
          onClick={toggleContextPanel}
          className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400"
          title="Close panel"
        >
          ✕
        </button>
      </div>

      <div className="flex-1 overflow-y-auto space-y-3">
        <SidecarDiagnostics />

        {/* Phase 3 Track E — local artifact records + open */}
        <ArtifactSidecarRecords />

        {/* Session info from streaming */}
        {lastAssistant?.traceId && (
          <Section title="Session">
            <KeyValue label="Trace" value={lastAssistant.traceId} />
            {lastAssistant.model && <KeyValue label="Model" value={lastAssistant.model} />}
            {lastAssistant.sessionId && <KeyValue label="Session" value={lastAssistant.sessionId} />}
            {lastAssistant.finishReason && <KeyValue label="Status" value={lastAssistant.finishReason} />}
          </Section>
        )}

        {/* Tool calls */}
        {lastAssistant?.toolCalls?.length > 0 && (
          <Section title="Tool Calls">
            <ul className="space-y-2">
              {lastAssistant.toolCalls.map((tc, i) => (
                <li key={tc.id || i} className="rounded bg-gray-50 dark:bg-gray-800 p-2">
                  <span className="text-xs font-mono font-medium text-purple-600 dark:text-purple-400">
                    {tc.name}
                  </span>
                  {tc.arguments && (
                    <pre className="mt-1 text-xs text-gray-500 dark:text-gray-400 overflow-x-auto whitespace-pre-wrap max-h-24">
                      {typeof tc.arguments === 'string' ? tc.arguments : JSON.stringify(tc.arguments, null, 2)}
                    </pre>
                  )}
                </li>
              ))}
            </ul>
          </Section>
        )}

        {lastAssistant?.toolResults?.length > 0 && (
          <Section title="Tool Results">
            <ul className="space-y-2">
              {lastAssistant.toolResults.map((tr, i) => (
                <li key={`${tr.tool_call_id}-${i}`} className="rounded bg-gray-50 dark:bg-gray-800 p-2 text-xs">
                  <span className="font-mono font-medium text-teal-600 dark:text-teal-400">
                    {tr.name || tr.tool_call_id || 'tool'}
                  </span>
                  {tr.auto_injected ? (
                    <span className="ml-2 text-amber-600 dark:text-amber-400 text-[10px] uppercase">auto</span>
                  ) : null}
                  <pre className="mt-1 text-gray-600 dark:text-gray-300 whitespace-pre-wrap break-words max-h-36 overflow-y-auto">
                    {tr.content?.length > 2000 ? `${tr.content.slice(0, 2000)}…` : tr.content || '—'}
                  </pre>
                </li>
              ))}
            </ul>
          </Section>
        )}

        {/* Formal analysis — degraded / risks / validation surfaced first */}
        {(contextData?.method ||
          contextData?.evidenceGrade ||
          contextData?.degraded ||
          (contextData?.evidenceChain && typeof contextData.evidenceChain === 'object')) && (
          <FormalReviewStripe contextData={contextData} />
        )}

        {/* Formal analysis context (from contextData) */}
        {contextData?.method && (
          <Section title="Method">
            <p className="text-sm text-gray-700 dark:text-gray-300">{contextData.method}</p>
          </Section>
        )}
        {contextData?.evidenceGrade && (
          <Section title="Evidence Grade">
            <GradeBadge grade={contextData.evidenceGrade} />
            {contextData.srGrade && (
              <span className="ml-2">
                <GradeBadge grade={contextData.srGrade} variant="amber" />
              </span>
            )}
          </Section>
        )}
        {contextData?.rationale && (
          <Section title="Rationale">
            <p className="text-xs text-gray-600 dark:text-gray-300">{contextData.rationale}</p>
          </Section>
        )}
        {contextData?.citations?.length > 0 && (
          <Section title="Citations">
            <ul className="space-y-1">
              {contextData.citations.map((c, i) => (
                <li key={i} className="text-xs text-blue-600 dark:text-blue-400 truncate" title={c}>
                  {c}
                </li>
              ))}
            </ul>
          </Section>
        )}
        {contextData?.assumptions?.length > 0 && (
          <Section title="Assumptions">
            <ul className="space-y-1">
              {contextData.assumptions.map((a, i) => (
                <li key={i} className="text-xs text-gray-500 dark:text-gray-400">
                  • {a}
                </li>
              ))}
            </ul>
          </Section>
        )}

        {contextData?.evidenceChain && typeof contextData.evidenceChain === 'object' && (
          <Section title="Formal evidence hints">
            <p className="text-[10px] text-gray-500 dark:text-gray-400 mb-1">
              Phase 3F1-style network grounding inspectability (non-prover hints).
            </p>
            {Array.isArray(contextData.evidenceChain.hints) && contextData.evidenceChain.hints.length > 0 ? (
              <ul className="space-y-0.5">
                {contextData.evidenceChain.hints.map((h, i) => (
                  <li key={`${String(h)}-${i}`} className="text-xs font-mono text-teal-700 dark:text-teal-300">
                    {h}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-gray-500">No extra hints emitted.</p>
            )}
            {typeof contextData.evidenceChain.distinct_host_count === 'number' ? (
              <p className="text-[11px] text-gray-600 dark:text-gray-300 mt-2">
                Hosts {contextData.evidenceChain.distinct_host_count}:{' '}
                {(contextData.evidenceChain.hosts || []).join(', ') || '—'}
              </p>
            ) : null}
            {contextData.evidenceChain.kb && typeof contextData.evidenceChain.kb === 'object' ? (
              <p className="text-[11px] text-gray-600 dark:text-gray-300 mt-1">
                KB tool citations {contextData.evidenceChain.kb.citation_entry_count ?? '—'} · distinct docs{' '}
                {contextData.evidenceChain.kb.distinct_documents ?? '—'}
              </p>
            ) : null}
            {(contextData.evidenceChain.overlap_http_uris?.length ?? 0) > 0 ? (
              <p className="text-[10px] text-amber-700 dark:text-amber-300 mt-1">
                HTTP overlap (web ∩ KB citations): {(contextData.evidenceChain.overlap_http_uris || []).join('; ')}
              </p>
            ) : null}
          </Section>
        )}

        {/* Sources from MRAG */}
        <Section title="Sources">
          <CitationList />
        </Section>
      </div>
    </div>
  )
}

/** Phase 3A A2 — inspect sidecar probe + /health payloads without leaving chat. */
function SidecarDiagnostics() {
  const [showRaw, setShowRaw] = useState(false)
  const [prefs, setPrefs] = useState(null)
  const [prefsErr, setPrefsErr] = useState(null)
  const [rulesSnap, setRulesSnap] = useState(null)
  const [rulesErr, setRulesErr] = useState(null)
  const [rulesManifestSnap, setRulesManifestSnap] = useState(null)
  const [rulesManifestErr, setRulesManifestErr] = useState(null)
  const [auditBundleCopied, setAuditBundleCopied] = useState(null)
  const [kbsSnap, setKbsSnap] = useState(null)
  const [kbsErr, setKbsErr] = useState(null)
  const mragKbId = useUiStore((s) => s.mragKbId)
  const setMragKbId = useUiStore((s) => s.setMragKbId)
  const runtimeStatus = useSidecarStatusStore((s) => s.runtimeStatus)
  const health = useSidecarStatusStore((s) => s.health)
  const refreshSidecarUi = useSidecarStatusStore((s) => s.refresh)

  const reloadPrefs = useCallback(async () => {
    try {
      const p = await fetchPreferences()
      setPrefs(p)
      setPrefsErr(null)
    } catch (e) {
      setPrefs(null)
      setPrefsErr(e?.message || String(e))
    }
  }, [])

  const reloadRules = useCallback(async () => {
    try {
      const r = await fetchRules()
      setRulesSnap(r)
      setRulesErr(null)
    } catch (e) {
      setRulesSnap(null)
      setRulesErr(e?.message || String(e))
    }
  }, [])

  const reloadRulesManifest = useCallback(async () => {
    try {
      const m = await fetchRulesManifest()
      setRulesManifestSnap(m)
      setRulesManifestErr(null)
    } catch (e) {
      setRulesManifestSnap(null)
      setRulesManifestErr(e?.message || String(e))
    }
  }, [])

  const reloadKbList = useCallback(async () => {
    try {
      const r = await listKnowledgeBases()
      setKbsSnap(r)
      setKbsErr(null)
    } catch (e) {
      setKbsSnap(null)
      setKbsErr(e?.message || String(e))
    }
  }, [])

  useEffect(() => {
    reloadPrefs()
    reloadRules()
    reloadRulesManifest()
    reloadKbList()
  }, [reloadPrefs, reloadKbList, reloadRules, reloadRulesManifest])

  const refreshAll = async () => {
    await refreshSidecarUi()
    await reloadPrefs()
    await reloadRules()
    await reloadRulesManifest()
    await reloadKbList()
  }

  const copyRulesAuditBundle = async () => {
    if (!rulesManifestSnap) return
    const text = JSON.stringify(rulesManifestSnap, null, 2)
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text)
      } else {
        throw new Error('no_clipboard_api')
      }
      setAuditBundleCopied(Date.now())
    } catch {
      try {
        const ta = document.createElement('textarea')
        ta.value = text
        document.body.appendChild(ta)
        ta.select()
        document.execCommand('copy')
        document.body.removeChild(ta)
        setAuditBundleCopied(Date.now())
      } catch {
        setAuditBundleCopied(null)
      }
    }
  }

  const url = runtimeStatus?.resolved_url || '—'
  const startup = runtimeStatus?.startup_state || '—'
  const attachErr =
    runtimeStatus?.last_error?.code ||
    (health?.ok === false ? (health.status === 0 ? 'attach_unreachable' : `http_${health.status}`) : '')
  const healthAgg =
    health?.ok === true && health.payload
      ? health.payload.status_label || health.payload.state || 'unknown'
      : health?.ok === false
        ? 'unreachable_or_error_response'
        : '—'

  return (
    <Section title="Sidecar runtime">
      <div className="space-y-1 text-xs">
        <KeyValue label="Base URL" value={url} />
        <KeyValue label="Startup" value={`${startup}${attachErr ? ` (${attachErr})` : ''}`} />
        <KeyValue label="/health aggregate" value={healthAgg} />

        <div className="pt-2 border-t border-gray-200 dark:border-gray-600 mt-1 space-y-1">
          <p className="text-[10px] font-medium uppercase text-gray-400">Preferences (GET /preferences)</p>
          {prefsErr ? (
            <p className="text-[10px] text-red-500 truncate" title={prefsErr}>
              {prefsErr}
            </p>
          ) : prefs ? (
            <>
              <KeyValue label="language" value={String(prefs.language ?? '—')} />
              <KeyValue label="analysis_conservatism" value={String(prefs.analysis_conservatism ?? '—')} />
              <KeyValue label="preferred_output_style" value={String(prefs.preferred_output_style ?? '—')} />
              {prefs.domain_hints?.length ? (
                <KeyValue label="domain_hints" value={`${prefs.domain_hints.length} items`} />
              ) : null}
            </>
          ) : (
            <p className="text-[10px] text-gray-500">Loading…</p>
          )}
        </div>

        <div className="pt-2 border-t border-gray-200 dark:border-gray-600 mt-1 space-y-1">
          <p className="text-[10px] font-medium uppercase text-gray-400">Rules (GET /rules)</p>
          {rulesErr ? (
            <p className="text-[10px] text-red-500 truncate" title={rulesErr}>
              {rulesErr}
            </p>
          ) : rulesSnap?.items?.length ? (
            <ul className="max-h-24 overflow-y-auto space-y-0.5">
              {rulesSnap.items.slice(0, 8).map((r, i) => (
                <li
                  key={`${r.path}-${i}`}
                  className="truncate text-[10px] text-gray-600 dark:text-gray-300 font-mono"
                  title={r.path}
                >
                  {typeof r.precedence_order === 'number' ? `[${r.precedence_order}]` : ''} {r.name}
                </li>
              ))}
              {rulesSnap.items.length > 8 ? (
                <li className="text-[10px] text-gray-500">…+{rulesSnap.items.length - 8} more</li>
              ) : null}
            </ul>
          ) : rulesSnap?.items?.length === 0 ? (
            <p className="text-[10px] text-gray-500">No ordered rule docs reported.</p>
          ) : (
            <p className="text-[10px] text-gray-500">Loading…</p>
          )}
        </div>

        <div className="pt-2 border-t border-gray-200 dark:border-gray-600 mt-1 space-y-1">
          <p className="text-[10px] font-medium uppercase text-gray-400">
            Rules manifest (GET /rules/manifest) — audit export
          </p>
          {rulesManifestErr ? (
            <p className="text-[10px] text-red-500 truncate" title={rulesManifestErr}>
              {rulesManifestErr}
            </p>
          ) : rulesManifestSnap ? (
            <>
              <KeyValue label="items" value={String(rulesManifestSnap.items?.length ?? 0)} />
              <KeyValue label="generated_at" value={String(rulesManifestSnap.generated_at_unix ?? '—')} />
              <button
                type="button"
                className="mt-1 w-full px-2 py-0.5 rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800 text-[10px] text-gray-600 dark:text-gray-300"
                onClick={() => copyRulesAuditBundle()}
              >
                Copy manifest JSON → clipboard
              </button>
              {auditBundleCopied ? (
                <p className="text-[10px] text-green-600 dark:text-green-400">Copied (audit bundle).</p>
              ) : null}
            </>
          ) : (
            <p className="text-[10px] text-gray-500">Loading…</p>
          )}
        </div>

        <div className="pt-2 border-t border-gray-200 dark:border-gray-600 mt-1 space-y-1">
          <p className="text-[10px] font-medium uppercase text-gray-400">MRAG KB for /retrieve</p>
          {kbsErr ? (
            <p className="text-[10px] text-red-500 truncate" title={kbsErr}>
              {kbsErr}
            </p>
          ) : Array.isArray(kbsSnap?.items) ? (
            <>
              <label className="block text-[10px] text-gray-500 mb-1">Prefer knowledge base</label>
              <select
                value={mragKbId ?? ''}
                onChange={(e) => setMragKbId(e.target.value)}
                className="w-full text-[10px] rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-1 py-1 text-gray-800 dark:text-gray-200"
              >
                <option value="">First KB in list</option>
                {kbsSnap.items.map((kb) => (
                  <option key={kb.knowledge_base_id} value={kb.knowledge_base_id}>
                    {(kb.name || kb.knowledge_base_id || '').slice(0, 40)} ({kb.documents ?? 0} docs)
                  </option>
                ))}
              </select>
            </>
          ) : (
            <p className="text-[10px] text-gray-500">Loading…</p>
          )}
        </div>

        <button
          type="button"
          className="mt-2 w-full px-2 py-1 rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-300"
          onClick={() => refreshAll()}
        >
          Refresh sidecar probes & snapshots
        </button>
        <button
          type="button"
          className="w-full px-2 py-1 rounded border border-dashed border-gray-300 dark:border-gray-600 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800"
          onClick={() => setShowRaw((v) => !v)}
        >
          {showRaw ? 'Hide raw JSON' : 'Show probe + health JSON'}
        </button>
        {showRaw ? (
          <pre className="mt-2 p-2 rounded bg-gray-900 text-gray-100 text-[10px] overflow-auto max-h-48 whitespace-pre-wrap break-words">
            {JSON.stringify({ runtime_snapshot: runtimeStatus, health_ipc: health }, null, 2)}
          </pre>
        ) : null}
      </div>
    </Section>
  )
}

/** Phase 3 Track E — list `GET /artifacts` and open file paths via Electron host bridge. */
function ArtifactSidecarRecords() {
  const [items, setItems] = useState([])
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(false)
  const [taskScope, setTaskScope] = useState('')
  const [lastNotice, setLastNotice] = useState(null)

  const load = useCallback(async () => {
    setBusy(true)
    setLastNotice(null)
    try {
      const trimmed = taskScope.trim()
      const r = await fetchArtifacts(trimmed || undefined)
      setItems(Array.isArray(r.items) ? r.items : [])
      setErr(null)
    } catch (e) {
      setErr(e?.message || String(e))
      setItems([])
    } finally {
      setBusy(false)
    }
  }, [taskScope])

  useEffect(() => {
    load()
    // Snapshot on mount only; Reload + task-id filter edits use `taskScope`.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- deliberate
  }, [])

  const openArtifactPath = async (absolutePath) => {
    const p = typeof absolutePath === 'string' ? absolutePath.trim() : ''
    if (!p) return
    if (window.desktopHost?.openPath) {
      try {
        const r = await window.desktopHost.openPath(p)
        if (!r?.ok) setLastNotice(r?.error || 'Open failed.')
        else setLastNotice(null)
      } catch (ie) {
        setLastNotice(ie?.message || String(ie))
      }
      return
    }
    if (navigator.clipboard?.writeText) {
      try {
        await navigator.clipboard.writeText(p)
        setLastNotice('Path copied (desktop bridge unavailable — e.g. dev in browser).')
      } catch (ce) {
        setLastNotice(ce?.message || String(ce))
      }
    }
  }

  const rows = [...items].sort((a, b) => (b.created_at_ns || 0) - (a.created_at_ns || 0))

  return (
    <Section title="Sidecar artifacts">
      <div className="space-y-2 text-xs">
        <p className="text-[10px] text-gray-500 dark:text-gray-400 leading-relaxed">
          Records from <code className="text-[10px]">GET /artifacts</code> · Open uses the Electron host (<code className="text-[10px]">shell.openPath</code>). In plain browser dev, fallback copies the absolute path.
        </p>
        <div className="flex gap-1 items-center">
          <input
            value={taskScope}
            onChange={(e) => setTaskScope(e.target.value)}
            placeholder="Optional task id filter…"
            className="flex-1 min-w-0 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-[11px]"
          />
          <button
            type="button"
            disabled={busy}
            onClick={() => load()}
            className="shrink-0 px-2 py-1 rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800 text-[11px] disabled:opacity-50"
          >
            {busy ? '…' : 'Reload'}
          </button>
        </div>
        {err ? (
          <p className="text-[10px] text-red-500 truncate" title={err}>
            {err}
          </p>
        ) : null}
        {lastNotice ? <p className="text-[10px] text-amber-600 dark:text-amber-400">{lastNotice}</p> : null}
        {rows.length === 0 && !err && !busy ? (
          <p className="text-[10px] text-gray-500">No artifacts yet (export Office or run agents that persist artifacts).</p>
        ) : (
          <ul className="max-h-40 overflow-y-auto space-y-1">
            {rows.slice(0, 16).map((a) => (
              <li
                key={a.artifact_id || a.path}
                className="rounded border border-gray-200 dark:border-gray-700 p-1.5 text-[10px]"
              >
                <div className="flex justify-between gap-2 items-start">
                  <span className="font-medium truncate text-gray-700 dark:text-gray-200" title={a.name}>
                    {a.name || 'artifact'}
                  </span>
                  <button
                    type="button"
                    onClick={() => openArtifactPath(a.path)}
                    className="shrink-0 px-1.5 py-0.5 rounded bg-blue-600/90 hover:bg-blue-700 text-white"
                  >
                    Open
                  </button>
                </div>
                <p className="text-gray-400 dark:text-gray-500 truncate font-mono mt-0.5" title={a.path}>
                  {a.path}
                </p>
                {a.task_id ? (
                  <p className="text-gray-400 dark:text-gray-500 mt-0.5 truncate" title={a.task_id}>
                    task: {a.task_id}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        )}
        {rows.length > 16 ? (
          <p className="text-[10px] text-gray-500">Showing 16 newest of {rows.length}.</p>
        ) : null}
      </div>
    </Section>
  )
}

/** Highlights degraded mode, harness risks, and `analysis_card.evidence_chain.validation` for formal runs. */
function FormalReviewStripe({ contextData }) {
  const degraded = Boolean(contextData?.degraded)
  const risks = Array.isArray(contextData?.risks) ? contextData.risks : []
  const v = contextData?.evidenceChain?.validation
  const conflicts = Array.isArray(v?.conflicts) ? v.conflicts : []
  const logicSignals = Array.isArray(v?.logic_signals) ? v.logic_signals : []
  const temporalSignals = Array.isArray(v?.temporal_signals) ? v.temporal_signals : []
  const policyHints = Array.isArray(v?.policy_hints) ? v.policy_hints : []
  const verification = Array.isArray(v?.delivery?.verification_next_steps) ? v.delivery.verification_next_steps : []

  const preview = (xs, max) => xs.filter((x) => typeof x === 'string' && x.trim()).slice(0, max)

  const hasEscalation = conflicts.length > 0 || preview(logicSignals, 8).length > 0 || preview(temporalSignals, 8).length > 0

  return (
    <Section title="Formal review snapshot">
      {degraded ? (
        <div
          className="mb-3 rounded-md border border-amber-600/90 bg-amber-50 px-3 py-2 dark:border-amber-500 dark:bg-amber-950/40"
          role="status"
          aria-live="polite"
        >
          <p className="text-xs font-semibold uppercase tracking-wide text-amber-900 dark:text-amber-200">
            Formal degraded mode
          </p>
          <p className="text-[11px] text-amber-900 dark:text-amber-100 mt-0.5 leading-relaxed">
            Harness reports degraded routing — treat outputs as exploratory; verify claims against evidence lanes.
          </p>
        </div>
      ) : null}

      {risks.length > 0 ? (
        <div className="mb-3 rounded-md border border-rose-300 bg-rose-50 px-3 py-2 dark:border-rose-600/70 dark:bg-rose-950/35">
          <p className="text-xs font-semibold text-rose-900 dark:text-rose-100">Formal risk notes</p>
          <ul className="mt-1 space-y-1">
            {risks.map((r, i) => (
              <li key={i} className="text-[11px] text-rose-800 dark:text-rose-200 leading-relaxed">
                • {r}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {v && typeof v === 'object' ? (
        <div className="rounded-md border border-teal-200 bg-teal-50/70 px-3 py-2 dark:border-teal-800 dark:bg-teal-950/30">
          <p className="text-xs font-semibold text-teal-900 dark:text-teal-100">Evidence chain validation (heuristic)</p>
          <p className="text-[10px] text-teal-800/90 dark:text-teal-300/90 mt-0.5">
            Conflicts {conflicts.length} · Logic signals {logicSignals.length} · Temporal {temporalSignals.length}
          </p>
          {hasEscalation ? (
            <p className="text-[10px] font-medium text-amber-700 dark:text-amber-400 mt-1">Review recommended before acting on causal claims.</p>
          ) : null}
          {conflicts.length > 0 ? (
            <details className="mt-2" open={conflicts.length <= 4}>
              <summary className="cursor-pointer text-[10px] text-teal-800 dark:text-teal-300 underline">
                Conflict previews ({Math.min(conflicts.length, 3)} shown)
              </summary>
              <ul className="mt-1 space-y-1 max-h-28 overflow-y-auto">
                {conflicts.slice(0, 3).map((c, i) => (
                  <li key={i} className="text-[10px] font-mono text-gray-700 dark:text-gray-300 break-words">
                    {String(c.kind || 'conflict')}: {(c.anchor_a || '').slice(0, 80)}{(c.anchor_a || '').length > 80 ? '…' : ''}{' — '}
                    {(c.anchor_b || '').slice(0, 80)}
                  </li>
                ))}
              </ul>
            </details>
          ) : null}
          {preview(logicSignals, 8).length > 0 ? (
            <div className="mt-2">
              <p className="text-[10px] font-medium text-teal-900 dark:text-teal-200">Logic / IPC scan signals</p>
              <ul className="space-y-0.5">
                {preview(logicSignals, 6).map((s, i) => (
                  <li key={i} className="text-[10px] font-mono text-gray-800 dark:text-gray-300 break-words">
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {preview(temporalSignals, 8).length > 0 ? (
            <div className="mt-2">
              <p className="text-[10px] font-medium text-teal-900 dark:text-teal-200">Temporal/version signals</p>
              <ul className="space-y-0.5">
                {preview(temporalSignals, 4).map((s, i) => (
                  <li key={i} className="text-[10px] font-mono text-gray-700 dark:text-gray-300 break-words">
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {preview(policyHints, 12).length > 0 ? (
            <details className="mt-2">
              <summary className="cursor-pointer text-[10px] text-teal-800 dark:text-teal-300 underline">
                Policy hints ({policyHints.length})
              </summary>
              <ul className="mt-1 space-y-0.5 max-h-32 overflow-y-auto">
                {preview(policyHints, 8).map((h, i) => (
                  <li key={i} className="text-[10px] text-teal-900 dark:text-teal-100 leading-snug">
                    • {h}
                  </li>
                ))}
              </ul>
            </details>
          ) : null}
          {verification.length > 0 ? (
            <div className="mt-2 border-t border-teal-200/80 pt-2 dark:border-teal-700/70">
              <p className="text-[10px] font-medium text-teal-900 dark:text-teal-100">Suggested verification steps</p>
              <ul className="space-y-0.5 mt-1">
                {verification.slice(0, 5).map((step, i) => (
                  <li key={i} className="text-[10px] text-teal-800 dark:text-teal-200 leading-snug">
                    {i + 1}. {step}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : (
        <p className="text-[10px] text-gray-500 dark:text-gray-400">Validation payload absent for this snapshot.</p>
      )}
    </Section>
  )
}

function Section({ title, children }) {
  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-3">
      <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wide">
        {title}
      </h4>
      {children}
    </div>
  )
}

function KeyValue({ label, value }) {
  return (
    <div className="flex justify-between items-center text-xs py-0.5">
      <span className="text-gray-500 dark:text-gray-400">{label}</span>
      <span className="text-gray-700 dark:text-gray-300 font-mono truncate max-w-[160px]" title={value}>
        {value}
      </span>
    </div>
  )
}

function GradeBadge({ grade, variant = 'green' }) {
  const colors = variant === 'green'
    ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
    : 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300'
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${colors}`}>
      {grade}
    </span>
  )
}
