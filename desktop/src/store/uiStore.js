import { create } from 'zustand'

const useUiStore = create((set) => ({
  sidebarCollapsed: false,
  contextPanelCollapsed: true,
  explorerPanelOpen: false,
  explorerOpenFile: null, // path of file currently open in viewer
  theme: 'dark',

  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  toggleContextPanel: () => set((s) => ({ contextPanelCollapsed: !s.contextPanelCollapsed })),
  toggleExplorerPanel: () => set((s) => ({ explorerPanelOpen: !s.explorerPanelOpen })),
  openFileInViewer: (filePath) => set({ explorerOpenFile: filePath }),
  closeFileViewer: () => set({ explorerOpenFile: null }),
  setTheme: (theme) => set({ theme }),

  // Context panel content (Formal/Meta snapshot; chat may refresh via setFormalContextSnapshot)
  contextData: null,
  /** When set, `/retrieve` uses this `knowledge_base_id`; unset → first KB from sidecar list. */
  mragKbId: null,
  setMragKbId: (id) => set({ mragKbId: typeof id === 'string' && id.trim() ? id.trim() : null }),
  /** Opens the context panel (user-driven navigation). */
  setContextData: (data) => set({ contextData: data, contextPanelCollapsed: false }),
  /** Replace right-rail snapshot without forcing the panel open (streaming formal path). */
  setFormalContextSnapshot: (data) => set({ contextData: data }),

  /** Increment when UI should open Sidebar → Settings (e.g. sidecar error banner CTA). */
  settingsPanelRequestNonce: 0,
  /** Expands sidebar and bumps nonce so Sidebar opens Settings overlay. */
  requestSettingsPanel: () =>
    set((s) => ({
      sidebarCollapsed: false,
      settingsPanelRequestNonce: s.settingsPanelRequestNonce + 1,
    })),
}))

export default useUiStore
