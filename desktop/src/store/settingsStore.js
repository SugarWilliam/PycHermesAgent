import { create } from 'zustand'

const STORAGE_KEY = 'pyc-hermes-settings'

const DEFAULTS = {
  sidecarUrl: 'http://127.0.0.1:8765',
  defaultModel: '',
  defaultAnalysisMode: 'casual',
  theme: 'dark'
}

const useSettingsStore = create((set, get) => ({
  ...DEFAULTS,

  loadSettings: () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (raw) {
        const parsed = JSON.parse(raw)
        set({ ...DEFAULTS, ...parsed })
      }
    } catch {
      // ignore corrupt storage
    }
  },

  saveSettings: (partial) => {
    const next = { ...get(), ...partial }
    const { loadSettings, saveSettings, ...data } = next
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
    set(partial)
  }
}))

export default useSettingsStore
