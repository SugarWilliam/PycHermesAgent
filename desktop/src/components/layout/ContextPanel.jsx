import useChatStore from '../../store/chatStore'
import useUiStore from '../../store/uiStore'
import useCitationStore from '../../store/citationStore'
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

        {/* Empty state */}
        {!lastAssistant?.traceId && !contextData && (
          <div className="flex items-center justify-center h-32">
            <p className="text-sm text-gray-400">No context available</p>
          </div>
        )}
      </div>
    </div>
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
