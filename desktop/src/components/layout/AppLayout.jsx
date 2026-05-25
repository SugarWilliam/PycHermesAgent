import { useState, useEffect } from 'react'
import Sidebar from './Sidebar'
import ContextPanel from './ContextPanel'
import ChatPanel from '../chat/ChatPanel'
import SidecarStatusBanner from './SidecarStatusBanner'
import FileExplorer from '../explorer/FileExplorer'
import FileViewer from '../explorer/FileViewer'
import SettingsPanel from '../settings/SettingsPanel'
import useUiStore from '../../store/uiStore'

export default function AppLayout() {
  const sidebarCollapsed = useUiStore((s) => s.sidebarCollapsed)
  const contextPanelCollapsed = useUiStore((s) => s.contextPanelCollapsed)
  const explorerPanelOpen = useUiStore((s) => s.explorerPanelOpen)
  const explorerOpenFile = useUiStore((s) => s.explorerOpenFile)
  const toggleExplorerPanel = useUiStore((s) => s.toggleExplorerPanel)
  const openFileInViewer = useUiStore((s) => s.openFileInViewer)
  const closeFileViewer = useUiStore((s) => s.closeFileViewer)
  const toggleContextPanel = useUiStore((s) => s.toggleContextPanel)
  const settingsPanelRequestNonce = useUiStore((s) => s.settingsPanelRequestNonce)

  const [settingsOpen, setSettingsOpen] = useState(false)

  // Open settings from external request (e.g. sidecar banner CTA)
  useEffect(() => {
    if (settingsPanelRequestNonce > 0) setSettingsOpen(true)
  }, [settingsPanelRequestNonce])

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100">
      {/* Left sidebar (sessions) */}
      <div
        className={`transition-all duration-300 ease-in-out overflow-hidden border-r border-gray-200 dark:border-gray-800 ${
          sidebarCollapsed ? 'w-0' : 'w-64'
        }`}
      >
        <Sidebar />
      </div>

      {/* Main content area */}
      <div className="flex-1 flex min-w-0 relative">
        {/* Top-right settings button (always visible) */}
        <button
          onClick={() => setSettingsOpen(true)}
          className="absolute top-2 right-2 z-30 p-1.5 rounded-lg hover:bg-gray-200/10 text-gray-400 hover:text-gray-200 transition-colors"
          title="设置"
        >
          <svg width="18" height="18" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M10 13a3 3 0 100-6 3 3 0 000 6z" />
            <path d="M16.5 10a6.5 6.5 0 01-.4 2.2l1.6 1.3-1.4 2.4-1.9-.6a6.5 6.5 0 01-1.9 1.1l-.4 2h-2.8l-.4-2a6.5 6.5 0 01-1.9-1.1l-1.9.6-1.4-2.4 1.6-1.3A6.5 6.5 0 013.5 10c0-.8.1-1.5.4-2.2L2.3 6.5l1.4-2.4 1.9.6A6.5 6.5 0 017.5 3.6l.4-2h2.8l.4 2a6.5 6.5 0 011.9 1.1l1.9-.6 1.4 2.4-1.6 1.3c.2.7.3 1.4.3 2.2z" />
          </svg>
        </button>

        {/* Chat panel - always visible, shrinks when file viewer is open */}
        <div className={`flex flex-col min-w-0 ${explorerOpenFile ? 'w-[400px] flex-shrink-0 border-r border-gray-200 dark:border-gray-800' : 'flex-1'}`}>
          <SidecarStatusBanner />
          <ChatPanel />
        </div>

        {/* File viewer - shown when a file is open */}
        {explorerOpenFile && (
          <div className="flex-1 flex flex-col min-w-0">
            <FileViewer filePath={explorerOpenFile} onClose={closeFileViewer} />
          </div>
        )}
      </div>

      {/* Right panel area */}
      <div className="flex flex-shrink-0">
        {/* Icon bar (always visible) */}
        <div className="w-10 flex flex-col items-center py-2 gap-2 border-l border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900">
          {/* Explorer toggle */}
          <button
            onClick={toggleExplorerPanel}
            className={`p-1.5 rounded transition-colors ${
              explorerPanelOpen
                ? 'bg-cyan-500/10 text-cyan-400'
                : 'text-gray-400 hover:text-gray-200 hover:bg-gray-700/50'
            }`}
            title="资源管理器"
          >
            <svg width="18" height="18" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
              <rect x="3" y="2" width="14" height="16" rx="1.5" />
              <path d="M7 6h6M7 10h6M7 14h4" />
            </svg>
          </button>
          {/* Context panel toggle */}
          <button
            onClick={toggleContextPanel}
            className={`p-1.5 rounded transition-colors ${
              !contextPanelCollapsed
                ? 'bg-cyan-500/10 text-cyan-400'
                : 'text-gray-400 hover:text-gray-200 hover:bg-gray-700/50'
            }`}
            title="上下文面板"
          >
            <svg width="18" height="18" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
              <circle cx="10" cy="10" r="7" />
              <path d="M10 7v3l2 2" />
            </svg>
          </button>
        </div>

        {/* Explorer panel */}
        <div
          className={`transition-all duration-300 ease-in-out overflow-hidden border-l border-gray-200 dark:border-gray-800 ${
            explorerPanelOpen ? 'w-64' : 'w-0'
          }`}
        >
          <FileExplorer onFileOpen={openFileInViewer} />
        </div>

        {/* Context panel */}
        <div
          className={`transition-all duration-300 ease-in-out overflow-hidden border-l border-gray-200 dark:border-gray-800 ${
            contextPanelCollapsed ? 'w-0' : 'w-80'
          }`}
        >
          <ContextPanel />
        </div>
      </div>

      {/* Settings overlay */}
      <SettingsPanel open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  )
}
