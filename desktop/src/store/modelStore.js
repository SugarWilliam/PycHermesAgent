/**
 * Shared model catalog store.
 *
 * Fetches models and providers from the sidecar once and makes them available
 * to any component (ChatInput model selector, SettingsPanel, etc).
 */
import { create } from 'zustand'
import { fetchModels, fetchProviders } from '../services/sidecarClient'

const useModelStore = create((set, get) => ({
  models: [],
  providers: [],
  loading: false,
  error: null,
  lastFetched: 0,

  /**
   * Fetch models + providers from sidecar. Caches for 60s unless force=true.
   */
  fetchCatalog: async (force = false) => {
    const now = Date.now()
    const { lastFetched, loading } = get()
    if (!force && loading) return
    if (!force && lastFetched && now - lastFetched < 60_000) return

    set({ loading: true, error: null })
    try {
      const [modRes, provRes] = await Promise.allSettled([fetchModels(), fetchProviders()])
      const models = modRes.status === 'fulfilled' ? (modRes.value?.items || []) : get().models
      const providers = provRes.status === 'fulfilled' ? (provRes.value?.items || []) : get().providers
      set({ models, providers, loading: false, lastFetched: Date.now() })
    } catch (err) {
      set({ loading: false, error: err.message || String(err) })
    }
  },

  /**
   * Get provider display name by id.
   */
  getProviderName: (providerId) => {
    const { providers } = get()
    const found = providers.find((p) => p.id === providerId)
    return found?.name || providerId
  }
}))

export default useModelStore
