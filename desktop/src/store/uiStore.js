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
  /** When set, `/retrieve` uses this `knowledge_base_id`; unset → first KB from sidecar list. */
  mragKbId: null,
  setMragKbId: (id) => set({ mragKbId: typeof id === 'string' && id.trim() ? id.trim() : null }),
  /** Opens the context panel (user-driven navigation). */
  setContextData: (data) => set({ contextData: data, contextPanelCollapsed: false }),
  /** Replace right-rail snapshot without forcing the panel open (streaming formal path). */
  setFormalContextSnapshot: (data) => set({ contextData: data })
}))

export default useUiStore
