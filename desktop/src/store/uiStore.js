import { create } from 'zustand'

const useUiStore = create((set) => ({
  sidebarCollapsed: false,
  contextPanelCollapsed: true,
  theme: 'dark',

  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  toggleContextPanel: () => set((s) => ({ contextPanelCollapsed: !s.contextPanelCollapsed })),
  setTheme: (theme) => set({ theme }),

  // Context panel content
  contextData: null,
  setContextData: (data) => set({ contextData: data, contextPanelCollapsed: false })
}))

export default useUiStore
