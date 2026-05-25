import MessageList from './MessageList'
import ChatInput from './ChatInput'
import WelcomeScreen from './WelcomeScreen'
import useChatStore from '../../store/chatStore'
import useUiStore from '../../store/uiStore'

export default function ChatPanel() {
  const activeConversationId = useChatStore((s) => s.activeConversationId)
  const conversations = useChatStore((s) => s.conversations)
  const toggleSidebar = useUiStore((s) => s.toggleSidebar)
  const sidebarCollapsed = useUiStore((s) => s.sidebarCollapsed)
  const sendMessage = useChatStore((s) => s.sendMessage)
  const createConversation = useChatStore((s) => s.createConversation)

  const activeConversation = conversations.find((c) => c.id === activeConversationId)

  const handleQuickAction = (text) => {
    if (!activeConversationId) createConversation()
    setTimeout(() => sendMessage(text, 'casual'), 50)
  }

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
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M3 4h12M3 9h12M3 14h12" /></svg>
          </button>
        )}
        <h2 className="text-sm font-medium truncate text-gray-900 dark:text-gray-100">
          {activeConversation ? activeConversation.title : 'PycHermesAgent'}
        </h2>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-hidden">
        {activeConversation ? (
          <MessageList messages={activeConversation.messages} />
        ) : (
          <WelcomeScreen onQuickAction={handleQuickAction} />
        )}
      </div>

      {/* Input */}
      <ChatInput />
    </div>
  )
}
