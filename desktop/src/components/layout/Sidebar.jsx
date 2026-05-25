import { useState } from 'react'
import useChatStore from '../../store/chatStore'
import useUiStore from '../../store/uiStore'
import SkillPanel from '../skills/SkillPanel'

function groupByDate(conversations) {
  const now = new Date()
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  const today = []
  const earlier = []
  for (const conv of conversations) {
    if (conv.createdAt >= todayStart) today.push(conv)
    else earlier.push(conv)
  }
  return { today, earlier }
}

export default function Sidebar() {
  const conversations = useChatStore((s) => s.conversations)
  const activeConversationId = useChatStore((s) => s.activeConversationId)
  const createConversation = useChatStore((s) => s.createConversation)
  const setActiveConversation = useChatStore((s) => s.setActiveConversation)
  const deleteConversation = useChatStore((s) => s.deleteConversation)
  const toggleSidebar = useUiStore((s) => s.toggleSidebar)
  const [skillsExpanded, setSkillsExpanded] = useState(false)

  const { today, earlier } = groupByDate(conversations)

  return (
    <div className="flex flex-col h-full w-64 bg-white dark:bg-gray-900 p-3">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
          Chats
        </span>
        <button
          onClick={toggleSidebar}
          className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400"
          title="Collapse sidebar"
        >
          ✕
        </button>
      </div>

      {/* New chat button */}
      <button
        onClick={createConversation}
        className="w-full mb-3 px-3 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium transition-colors"
      >
        + New Chat
      </button>

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto space-y-1">
        <ConversationGroup
          label="Today"
          items={today}
          activeId={activeConversationId}
          onSelect={setActiveConversation}
          onDelete={deleteConversation}
        />
        <ConversationGroup
          label="Earlier"
          items={earlier}
          activeId={activeConversationId}
          onSelect={setActiveConversation}
          onDelete={deleteConversation}
        />
      </div>

      {/* Skills panel */}
      <SkillPanel expanded={skillsExpanded} onToggle={() => setSkillsExpanded(!skillsExpanded)} />
    </div>
  )
}

function ConversationGroup({ label, items, activeId, onSelect, onDelete }) {
  if (!items.length) return null
  return (
    <div className="mb-2">
      <span className="px-3 text-xs font-medium text-gray-400 dark:text-gray-500 uppercase">
        {label}
      </span>
      <div className="mt-1 space-y-0.5">
        {items.map((conv) => (
          <ConversationItem
            key={conv.id}
            conv={conv}
            active={conv.id === activeId}
            onSelect={onSelect}
            onDelete={onDelete}
          />
        ))}
      </div>
    </div>
  )
}

function ConversationItem({ conv, active, onSelect, onDelete }) {
  return (
    <div
      className={`group flex items-center rounded-lg transition-colors cursor-pointer ${
        active
          ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
          : 'hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300'
      }`}
    >
      <button
        onClick={() => onSelect(conv.id)}
        className="flex-1 text-left px-3 py-2 text-sm truncate"
      >
        {conv.title}
      </button>
      <button
        onClick={(e) => { e.stopPropagation(); onDelete(conv.id) }}
        className="hidden group-hover:block px-2 text-xs text-gray-400 hover:text-red-500"
        title="Delete"
      >
        ✕
      </button>
    </div>
  )
}
