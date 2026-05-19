import MessageList from './MessageList'
import ChatInput from './ChatInput'
import useChatStore from '../../store/chatStore'
import useUiStore from '../../store/uiStore'

export default function ChatPanel() {
  const activeConversationId = useChatStore((s) => s.activeConversationId)
  const conversations = useChatStore((s) => s.conversations)
  const toggleSidebar = useUiStore((s) => s.toggleSidebar)
  const sidebarCollapsed = useUiStore((s) => s.sidebarCollapsed)

  const activeConversation = conversations.find((c) => c.id === activeConversationId)

  return (
    <div className="flex flex-col h-full">
      {/* Top bar */}
      <div className="flex items-center px-4 py-3 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
        {sidebarCollapsed && (
          <button
            onClick={toggleSidebar}
            className="mr-3 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500"
            title="Show sidebar"
          >
            ☰
          </button>
        )}
        <h2 className="text-sm font-medium truncate">
          {activeConversation ? activeConversation.title : 'PycHermesAgent'}
        </h2>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-hidden">
        {activeConversation ? (
          <MessageList messages={activeConversation.messages} />
        ) : (
          <div className="flex items-center justify-center h-full">
            <p className="text-gray-400 text-sm">Start a new conversation</p>
          </div>
        )}
      </div>

      {/* Input */}
      <ChatInput />
    </div>
  )
}
