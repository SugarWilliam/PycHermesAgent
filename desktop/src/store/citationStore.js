import { create } from 'zustand'

const useCitationStore = create((set) => ({
  citations: [],
  setCitations: (list) => set({ citations: list }),
  clearCitations: () => set({ citations: [] }),
}))

export default useCitationStore
