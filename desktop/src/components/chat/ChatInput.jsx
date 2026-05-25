import { useState, useCallback, useRef, useEffect } from 'react'
import useChatStore from '../../store/chatStore'
import useCitationStore from '../../store/citationStore'
import useUiStore from '../../store/uiStore'
import useSettingsStore from '../../store/settingsStore'
import useModelStore from '../../store/modelStore'
import { listKnowledgeBases, searchKnowledgeBase, ingestFileToKnowledgeBase, ingestPdfToKnowledgeBase } from '../../services/sidecarClient'
import useSlashCommands from '../../hooks/useSlashCommands'
import SlashMenu from './SlashMenu'
import ModelSelector from './ModelSelector'

const RETRIEVE_DEFAULT = Object.freeze({
  top_k: 8,
  retrieval_mode: 'hybrid',
  semantic_weight: 0.35,
  include_citations: true
})

const SUPPORTED_EXTENSIONS = ['.md', '.txt', '.pdf', '.docx', '.xlsx', '.pptx', '.html', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']



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

function PaperclipIcon({ className }) {
  return (
    <svg className={className} width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" />
    </svg>
  )
}

export default function ChatInput() {
  const [text, setText] = useState('')
  const [mode, setMode] = useState('casual')
  const [forceAnalyze, setForceAnalyze] = useState(false)
  const [attachedFiles, setAttachedFiles] = useState([])
  const [modelOverride, setModelOverride] = useState(null)
  const [showModelMenu, setShowModelMenu] = useState(false)
  const [isFocused, setIsFocused] = useState(false)
  const modelMenuRef = useRef(null)

  const isStreaming = useChatStore((s) => s.isStreaming)
  const sendMessage = useChatStore((s) => s.sendMessage)
  const stopStreaming = useChatStore((s) => s.stopStreaming)
  const createConversation = useChatStore((s) => s.createConversation)
  const deleteConversation = useChatStore((s) => s.deleteConversation)
  const activeConversationId = useChatStore((s) => s.activeConversationId)
  const addMessage = useChatStore((s) => s.addMessage)
  const setCitations = useCitationStore((s) => s.setCitations)
  const mragKbId = useUiStore((s) => s.mragKbId)
  const defaultModel = useSettingsStore((s) => s.settings?.defaultModel)
  const saveSettings = useSettingsStore((s) => s.saveSettings)
  const models = useModelStore((s) => s.models)
  const fetchCatalog = useModelStore((s) => s.fetchCatalog)

  // Fetch model catalog on mount
  useEffect(() => { fetchCatalog() }, [fetchCatalog])

  const currentModel = modelOverride || defaultModel || 'github-copilot/gpt-4.1'
  const currentModelLabel = models.find((m) => m.id === currentModel)?.name || currentModel.split('/').pop()

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

  const handlePickFiles = async () => {
    if (!window.desktopHost?.pickFiles) return
    try {
      const files = await window.desktopHost.pickFiles({
        multiple: true,
        filters: [
          { name: '支持的文件', extensions: SUPPORTED_EXTENSIONS.map((e) => e.slice(1)) }
        ]
      })
      if (files && files.length) {
        setAttachedFiles((prev) => [...prev, ...files])
      }
    } catch {
      // user cancelled or error
    }
  }

  const removeAttachment = (index) => {
    setAttachedFiles((prev) => prev.filter((_, i) => i !== index))
  }

  const ingestAttachments = async () => {
    if (!attachedFiles.length) return
    try {
      const { items = [] } = await listKnowledgeBases()
      if (!items.length) return
      const kbId = items[0].knowledge_base_id
      for (const file of attachedFiles) {
        const filePath = typeof file === 'string' ? file : file.path || file
        if (filePath.toLowerCase().endsWith('.pdf')) {
          await ingestPdfToKnowledgeBase(kbId, filePath)
        } else {
          await ingestFileToKnowledgeBase(kbId, filePath)
        }
      }
    } catch {
      // ingest errors are non-blocking for send
    }
  }

  const getFileName = (file) => {
    const path = typeof file === 'string' ? file : file.path || file.name || String(file)
    const parts = path.replace(/\\/g, '/').split('/')
    return parts[parts.length - 1] || path
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

    // Ingest attached files in background
    if (attachedFiles.length) {
      ingestAttachments()
    }

    // Build message text with attachment mentions
    let messageText = trimmed
    if (attachedFiles.length) {
      const fileNames = attachedFiles.map(getFileName).join(', ')
      messageText = `[📎 ${fileNames}]\n\n${trimmed}`
    }

    const effectiveMode = forceAnalyze ? 'formal' : mode
    sendMessage(messageText, effectiveMode, modelOverride || undefined)
    setText('')
    setAttachedFiles([])
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

      {/* Top row: mode selector + model selector */}
      <div className="flex items-center justify-between mb-2">
        {/* Analysis mode selector */}
        <div className="flex items-center gap-1">
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

        {/* Model selector */}
        <div className="relative" ref={modelMenuRef}>
          <button
            type="button"
            onClick={() => setShowModelMenu((v) => !v)}
            title="选择模型"
            className="flex items-center gap-1.5 text-xs bg-gray-800 border border-gray-700 rounded-full px-2.5 py-1 text-gray-300 hover:text-white hover:border-gray-500 transition-colors"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="opacity-60">
              <circle cx="12" cy="12" r="3" /><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
            </svg>
            {currentModelLabel}
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="opacity-50">
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>
          <ModelSelector
            open={showModelMenu}
            onClose={() => setShowModelMenu(false)}
            currentModel={currentModel}
            onSelect={(id) => { setModelOverride(id); saveSettings({ defaultModel: id }) }}
            position="above"
          />
        </div>
      </div>

      {/* Input area with glow effect */}
      <div
        className={`rounded-xl border transition-all duration-200 ${
          isFocused
            ? 'border-blue-500/60 shadow-[0_0_12px_2px_rgba(59,130,246,0.15)]'
            : 'border-gray-300 dark:border-gray-700'
        } bg-gray-50 dark:bg-gray-800`}
      >
        {/* Textarea row with attachment button */}
        <div className="flex items-end gap-2 px-3 py-2">
          {/* Paperclip attachment button */}
          <button
            type="button"
            onClick={handlePickFiles}
            title="附加文件"
            className="text-gray-400 hover:text-cyan-400 transition-colors pb-1 flex-shrink-0"
          >
            <PaperclipIcon className="w-[18px] h-[18px]" />
          </button>

          <textarea
            value={text}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder="Type a message... (/ for commands)"
            rows={1}
            disabled={isStreaming}
            className="flex-1 resize-none bg-transparent text-sm focus:outline-none disabled:opacity-50 py-1"
          />

          {isStreaming ? (
            <button
              type="button"
              onClick={stopStreaming}
              className="px-4 py-1.5 rounded-lg bg-red-600 hover:bg-red-700 text-white text-sm font-medium transition-colors flex-shrink-0"
            >
              Stop
            </button>
          ) : (
            <button
              type="submit"
              disabled={!text.trim() && !attachedFiles.length}
              className="px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium transition-colors flex-shrink-0"
            >
              Send
            </button>
          )}
        </div>

        {/* Attached files chips */}
        {attachedFiles.length > 0 && (
          <div className="flex flex-wrap gap-1.5 px-3 pb-2">
            {attachedFiles.map((file, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 bg-gray-700/60 text-gray-300 text-xs rounded-full px-2 py-0.5"
              >
                📎 {getFileName(file)}
                <button
                  type="button"
                  onClick={() => removeAttachment(i)}
                  className="text-gray-500 hover:text-red-400 ml-0.5"
                  title="移除"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}
      </div>
    </form>
  )
}
