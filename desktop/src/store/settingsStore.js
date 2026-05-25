import { create } from 'zustand'

const STORAGE_KEY = 'pyc-hermes-settings'

const DEFAULTS = {
  defaultModel: '',
  defaultAnalysisMode: 'casual',
  theme: 'dark',
  provider: '',
  apiKey: '',
  baseUrl: '',
  sendKey: 'enter'
}

// Provider environment variable keys that may be stored alongside settings
const PROVIDER_KEYS = ['GITHUB_TOKEN', 'OPENROUTER_API_KEY', 'OPENAI_API_KEY', 'OPENCODE_API_KEY']

function sanitizeSettings(input = {}) {
  const base = {
    defaultModel: typeof input.defaultModel === 'string' ? input.defaultModel : DEFAULTS.defaultModel,
    defaultAnalysisMode: ['casual', 'structured', 'formal'].includes(input.defaultAnalysisMode)
      ? input.defaultAnalysisMode
      : DEFAULTS.defaultAnalysisMode,
    theme: ['light', 'dark', 'system'].includes(input.theme) ? input.theme : DEFAULTS.theme,
    provider: typeof input.provider === 'string' ? input.provider : DEFAULTS.provider,
    apiKey: typeof input.apiKey === 'string' ? input.apiKey : DEFAULTS.apiKey,
    baseUrl: typeof input.baseUrl === 'string' ? input.baseUrl : DEFAULTS.baseUrl,
    sendKey: ['enter', 'ctrl+enter'].includes(input.sendKey) ? input.sendKey : DEFAULTS.sendKey
  }
  // Preserve provider credential keys (stored as non-empty strings)
  for (const key of PROVIDER_KEYS) {
    if (typeof input[key] === 'string' && input[key]) {
      base[key] = input[key]
    }
  }
  return base
}

const useSettingsStore = create((set, get) => ({
  // The settings object (reactive)
  settings: { ...DEFAULTS },

  loadSettings: () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (!raw) return
      set({ settings: sanitizeSettings(JSON.parse(raw)) })
    } catch {
      // ignore corrupt storage
    }
  },

  saveSettings: (next) => {
    const current = get().settings || {}
    const merged = sanitizeSettings({ ...current, ...next })
    localStorage.setItem(STORAGE_KEY, JSON.stringify(merged))
    set({ settings: merged })
  }
}))

export default useSettingsStore
