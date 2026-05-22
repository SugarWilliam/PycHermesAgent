import { create } from 'zustand'

const useCitationStore = create((set, get) => ({
  citations: [],
  setCitations: (list) => set({ citations: Array.isArray(list) ? list : [] }),
  appendCitations: (list) => {
    if (!Array.isArray(list) || list.length === 0) return
    const prev = get().citations
    const seen = new Set(prev.map((c) => `${c.chunk_id || ''}|${c.source_uri || ''}|${c.snippet?.slice(0, 40) || ''}`))
    const merged = [...prev]
    for (const c of list) {
      const key = `${c.chunk_id || ''}|${c.source_uri || ''}|${(c.snippet || '').slice(0, 40)}`
      if (seen.has(key)) continue
      seen.add(key)
      merged.push(c)
    }
    set({ citations: merged })
  },
  clearCitations: () => set({ citations: [] }),
}))

export default useCitationStore
