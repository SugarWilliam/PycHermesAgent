import { create } from 'zustand'

const STORAGE_KEY = 'pyc-hermes-settings'

const DEFAULTS = {
  defaultModel: '',
  defaultAnalysisMode: 'casual',
  theme: 'dark'
}

function sanitizeSettings(input = {}) {
  return {
    defaultModel: typeof input.defaultModel === 'string' ? input.defaultModel : DEFAULTS.defaultModel,
    defaultAnalysisMode: ['casual', 'structured', 'formal'].includes(input.defaultAnalysisMode)
      ? input.defaultAnalysisMode
      : DEFAULTS.defaultAnalysisMode,
    theme: ['light', 'dark', 'system'].includes(input.theme) ? input.theme : DEFAULTS.theme
  }
}

const useSettingsStore = create((set, get) => ({
  ...DEFAULTS,

  loadSettings: () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (!raw) return
      set(sanitizeSettings(JSON.parse(raw)))
    } catch {
      // ignore corrupt storage
    }
  },

  saveSettings: (partial) => {
    const next = sanitizeSettings({ ...get(), ...partial })
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    set(next)
  }
}))

export default useSettingsStore
