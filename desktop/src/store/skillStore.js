import { create } from 'zustand'
import { fetchSkills, activateSkill, deactivateSkill } from '../services/sidecarClient'

const useSkillStore = create((set, get) => ({
  skills: [],
  loading: false,

  fetchSkills: async () => {
    set({ loading: true })
    try {
      const payload = await fetchSkills()
      const discovered = (Array.isArray(payload.items) ? payload.items : []).map((skill) => ({
        ...skill,
        sourceKind: skill.source_kind || 'project',
        activatable: false
      }))
      const builtin = (Array.isArray(payload.builtin) ? payload.builtin : []).map((skill) => ({
        ...skill,
        sourceKind: 'builtin',
        activatable: true
      }))
      set({ skills: [...builtin, ...discovered], loading: false })
    } catch {
      set({ loading: false })
    }
  },

  activateSkill: async (id) => {
    const prev = get().skills
    set({ skills: prev.map((s) => (s.id === id ? { ...s, active: true } : s)) })
    try {
      await activateSkill(id)
    } catch {
      set({ skills: prev })
    }
  },

  deactivateSkill: async (id) => {
    const prev = get().skills
    set({ skills: prev.map((s) => (s.id === id ? { ...s, active: false } : s)) })
    try {
      await deactivateSkill(id)
    } catch {
      set({ skills: prev })
    }
  },

  getActiveFragments: () => get().skills.filter((s) => s.active).map((s) => s.name)
}))

export default useSkillStore
