import { create } from 'zustand'

const useUiStore = create((set) => ({
  sidebarCollapsed: false,
  contextPanelCollapsed: true,
  theme: 'dark',

  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  toggleContextPanel: () => set((s) => ({ contextPanelCollapsed: !s.contextPanelCollapsed })),
  setTheme: (theme) => set({ theme }),

  // Context panel content (Formal/Meta snapshot; chat may refresh via setFormalContextSnapshot)
  contextData: null,
  /** Opens the context panel (user-driven navigation). */
  setContextData: (data) => set({ contextData: data, contextPanelCollapsed: false }),
  /** Replace right-rail snapshot without forcing the panel open (streaming formal path). */
  setFormalContextSnapshot: (data) => set({ contextData: data })
}))

export default useUiStore
