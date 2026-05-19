import { useState, useCallback } from 'react'
import useChatStore from '../../store/chatStore'
import useSlashCommands from '../../hooks/useSlashCommands'
import SlashMenu from './SlashMenu'

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
          '/retrieve — Search knowledge bases'
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
        addMessage(cid, { role: 'assistant', content: '🔍 Knowledge base search coming soon.' })
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

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!text.trim() || isStreaming) return
    const effectiveMode = forceAnalyze ? 'formal' : mode
    sendMessage(text.trim(), effectiveMode)
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
