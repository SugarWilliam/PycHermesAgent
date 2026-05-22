import Sidebar from './Sidebar'
import ContextPanel from './ContextPanel'
import ChatPanel from '../chat/ChatPanel'
import SidecarStatusBanner from './SidecarStatusBanner'
import useUiStore from '../../store/uiStore'

export default function AppLayout() {
  const sidebarCollapsed = useUiStore((s) => s.sidebarCollapsed)
  const contextPanelCollapsed = useUiStore((s) => s.contextPanelCollapsed)

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100">
      {/* Left sidebar */}
      <div
        className={`transition-all duration-300 ease-in-out overflow-hidden border-r border-gray-200 dark:border-gray-800 ${
          sidebarCollapsed ? 'w-0' : 'w-64'
        }`}
      >
        <Sidebar />
      </div>

      {/* Center chat panel */}
      <div className="flex-1 flex flex-col min-w-0">
        <SidecarStatusBanner />
        <ChatPanel />
      </div>

      {/* Right context panel */}
      <div
        className={`transition-all duration-300 ease-in-out overflow-hidden border-l border-gray-200 dark:border-gray-800 ${
          contextPanelCollapsed ? 'w-0' : 'w-80'
        }`}
      >
        <ContextPanel />
      </div>
    </div>
  )
}
