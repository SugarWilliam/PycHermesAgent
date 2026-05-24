import { useState, useCallback } from 'react'
import useChatStore from '../../store/chatStore'
import useCitationStore from '../../store/citationStore'
import useUiStore from '../../store/uiStore'
import { listKnowledgeBases, searchKnowledgeBase } from '../../services/sidecarClient'
import useSlashCommands from '../../hooks/useSlashCommands'
import SlashMenu from './SlashMenu'

const RETRIEVE_DEFAULT = Object.freeze({
  top_k: 8,
  retrieval_mode: 'hybrid',
  semantic_weight: 0.35,
  include_citations: true
})

function hitsToCitationLike(hits) {
  if (!Array.isArray(hits)) return []
  return hits.map((h) => ({
    chunk_id: h.chunk_id || '',
    document_id: h.document_id || '',
    title: (h.metadata && h.metadata.title) || '',
    source_type: (h.metadata && h.metadata.source_type) || '',
    source_uri: (h.metadata && h.metadata.source_uri) || '',
    page: h.metadata?.page != null ? h.metadata.page : null,
    section: (h.metadata && h.metadata.section) || '',
    relevance: typeof h.score === 'number' ? h.score : 0,
    snippet: h.snippet || ''
  }))
}

function formatRetrieveMarkdown({ kbName, kbId, mode, semanticWeight }, result) {
  const lines = [`**MRAG** · KB \`${kbName || kbId}\` (\`${kbId}\`) · mode \`${mode}\` · semantic_weight \`${semanticWeight}\``, '']
  if (result?.warnings?.length) {
    for (const w of result.warnings) lines.push(`- ⚠️ ${w}`)
    lines.push('')
  }
  const hits = Array.isArray(result?.hits) ? result.hits : []
  if (hits.length === 0) {
    lines.push('_No hits (empty KB or nothing matched)._')
    return lines.join('\n')
  }
  hits.forEach((h, i) => {
    const sec = h.metadata?.section || ''
    const page = h.metadata?.page != null ? ` · p.${h.metadata.page}` : ''
    lines.push(`${i + 1}. **${Number(h.score).toFixed(3)}**${page}${sec ? ` · ${sec}` : ''}`)
    lines.push(`   ${(h.snippet || '').slice(0, 400)}${(h.snippet || '').length > 400 ? '…' : ''}`)
    if (h.chunk_id) lines.push(`   \`chunk_id\`: ${h.chunk_id}`)
    lines.push('')
  })
  return lines.join('\n').trimEnd()
}

const MODES = [
  { value: 'casual', label: 'Casual', desc: 'Quick chat, no formal analysis' },
  { value: 'structured', label: 'Structured', desc: 'Systematic reasoning with guardrails' },
  { value: 'formal', label: 'Formal', desc: 'Full MetaHarness formal analysis pipeline' }
]

export default function ChatInput() {
  const [text, setText] = useState('')
  const [mode, setMode] = useState('casual')
  const [forceAnalyze, setForceAnalyze] = useState(false)
  const isStreaming = useChatStore((s) => s.isStreaming)
  const sendMessage = useChatStore((s) => s.sendMessage)
  const stopStreaming = useChatStore((s) => s.stopStreaming)
  const createConversation = useChatStore((s) => s.createConversation)
  const deleteConversation = useChatStore((s) => s.deleteConversation)
  const activeConversationId = useChatStore((s) => s.activeConversationId)
  const addMessage = useChatStore((s) => s.addMessage)
  const setCitations = useCitationStore((s) => s.setCitations)
  const mragKbId = useUiStore((s) => s.mragKbId)

  const handleExecute = useCallback((cmd) => {
    setText('')
    switch (cmd.name) {
      case 'casual':
      case 'structured':
      case 'formal':
        setMode(cmd.name)
        break
      case 'clear':
        if (activeConversationId) deleteConversation(activeConversationId)
        break
      case 'new':
        createConversation()
        break
      case 'help': {
        const helpText = '**Available commands:**\n' +
          '/casual — Switch to casual mode\n' +
          '/structured — Switch to structured mode\n' +
          '/formal — Switch to formal analysis mode\n' +
          '/clear — Clear current conversation\n' +
          '/new — Start new conversation\n' +
          '/analyze — Force formal analysis on next message\n' +
          '/retrieve <query> — MRAG hybrid search (KB: Context panel, or first in list)'
        let convId = activeConversationId
        if (!convId) convId = createConversation()
        addMessage(convId, { role: 'assistant', content: helpText })
        break
      }
      case 'analyze':
        setMode('formal')
        setForceAnalyze(true)
        break
      case 'retrieve': {
        let cid = activeConversationId
        if (!cid) cid = createConversation()
        addMessage(cid, {
          role: 'assistant',
          content:
            '**`/retrieve`** — run a hybrid MRAG query against your local KBs.\n\n' +
            '**Usage:** `/retrieve your search terms`\n\n' +
            'Pick a KB under **Context → Sidecar runtime → MRAG KB for /retrieve**. If unchanged, sidecar **`GET /knowledge-bases` first item** is used.'
        })
        break
      }
    }
  }, [activeConversationId, deleteConversation, createConversation, addMessage])

  const slash = useSlashCommands({ onExecute: handleExecute })

  const handleChange = (e) => {
    const val = e.target.value
    setText(val)
    if (val.startsWith('/')) {
      slash.open(val.slice(1))
    } else if (slash.isOpen) {
      slash.close()
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const trimmed = text.trim()
    if (!trimmed || isStreaming) return

    const retrieveMatch = trimmed.match(/^\/retrieve(?:\s+(.*))?$/i)
    if (retrieveMatch) {
      const q = (retrieveMatch[1] || '').trim()
      setText('')
      setForceAnalyze(false)
      let convId = activeConversationId
      if (!convId) convId = createConversation()
      if (!q) {
        addMessage(convId, {
          role: 'assistant',
          content:
            '**`/retrieve`** needs a query after the command.\n\n**Example:** `/retrieve deployment checklist`'
        })
        return
      }
      addMessage(convId, { role: 'user', content: trimmed })
      addMessage(convId, { role: 'assistant', content: '🔍 _Searching knowledge base…_' })
      try {
        const { items = [] } = await listKnowledgeBases()
        if (!items.length) {
          useChatStore.getState().updateLastAssistantMeta(convId, {
            content: 'No knowledge bases yet. Create/ingest via sidecar MRAG endpoints, then retry.'
          })
          setCitations([])
          return
        }
        const preferred = mragKbId ? items.find((x) => x.knowledge_base_id === mragKbId) : null
        const kbRecord = preferred || items[0]
        const kbId = kbRecord.knowledge_base_id
        const kbName = kbRecord.name || ''
        const payload = {
          query: q,
          top_k: RETRIEVE_DEFAULT.top_k,
          retrieval_mode: RETRIEVE_DEFAULT.retrieval_mode,
          semantic_weight: RETRIEVE_DEFAULT.semantic_weight,
          include_citations: RETRIEVE_DEFAULT.include_citations
        }
        const result = await searchKnowledgeBase(kbId, payload)
        const citeList = Array.isArray(result.citations) ? result.citations : []
        const forPanel = citeList.length ? citeList : hitsToCitationLike(result.hits)
        setCitations(forPanel)
        let body = formatRetrieveMarkdown(
          { kbName, kbId, mode: payload.retrieval_mode, semanticWeight: payload.semantic_weight },
          result
        )
        if (mragKbId && !preferred && items.length) {
          body = `_Preferred KB id is not on the server list; searched the first KB._\n\n${body}`
        }
        useChatStore.getState().updateLastAssistantMeta(convId, { content: body })
      } catch (err) {
        const msg = err?.message || String(err)
        useChatStore.getState().updateLastAssistantMeta(convId, {
          content: `**Retrieve failed.** ${msg}`
        })
        setCitations([])
      }
      return
    }

    const effectiveMode = forceAnalyze ? 'formal' : mode
    sendMessage(trimmed, effectiveMode)
    setText('')
    setForceAnalyze(false)
  }

  const handleKeyDown = (e) => {
    if (slash.handleKeyDown(e)) return
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="relative border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-4 py-3"
    >
      {/* Slash command menu */}
      {slash.isOpen && (
        <SlashMenu
          commands={slash.commands}
          selectedIndex={slash.selectedIndex}
          onSelect={slash.execute}
        />
      )}

      {/* Analysis mode selector */}
      <div className="flex items-center gap-1 mb-2">
        {MODES.map((m) => (
          <button
            key={m.value}
            type="button"
            onClick={() => setMode(m.value)}
            title={m.desc}
            className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
              mode === m.value
                ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300'
                : 'text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800'
            }`}
          >
            {m.label}
          </button>
        ))}
        <span className="ml-2 text-xs text-gray-400 hidden sm:inline">
          {forceAnalyze ? '⚡ Next message: forced formal analysis' : MODES.find((m) => m.value === mode)?.desc}
        </span>
      </div>

      {/* Text area + actions */}
      <div className="flex items-end gap-2">
        <textarea
          value={text}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder="Type a message... (/ for commands)"
          rows={1}
          disabled={isStreaming}
          className="flex-1 resize-none rounded-lg border border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 disabled:opacity-50"
        />
        {isStreaming ? (
          <button
            type="button"
            onClick={stopStreaming}
            className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white text-sm font-medium transition-colors"
          >
            Stop
          </button>
        ) : (
          <button
            type="submit"
            disabled={!text.trim()}
            className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium transition-colors"
          >
            Send
          </button>
        )}
      </div>
    </form>
  )
}
