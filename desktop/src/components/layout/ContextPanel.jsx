import { useEffect, useState, useCallback } from 'react'
import useChatStore from '../../store/chatStore'
import useUiStore from '../../store/uiStore'
import { useSidecarStatusStore } from '../../store/sidecarStatusStore'
import { fetchPreferences } from '../../services/sidecarClient'
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
        {contextData?.risks?.length > 0 && (
          <Section title="Risks">
            <ul className="space-y-1">
              {contextData.risks.map((r, i) => (
                <li key={i} className="text-xs text-amber-600 dark:text-amber-400">
                  • {r}
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

  useEffect(() => {
    reloadPrefs()
  }, [reloadPrefs])

  const refreshAll = async () => {
    await refreshSidecarUi()
    await reloadPrefs()
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

        <button
          type="button"
          className="mt-2 w-full px-2 py-1 rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-300"
          onClick={() => refreshAll()}
        >
          Refresh probes & preferences
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
