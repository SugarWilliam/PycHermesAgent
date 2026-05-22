import { useEffect } from 'react'
import useSkillStore from '../../store/skillStore'
import SkillCard from './SkillCard'

export default function SkillPanel({ expanded, onToggle }) {
  const skills = useSkillStore((s) => s.skills)
  const loading = useSkillStore((s) => s.loading)
  const fetchSkills = useSkillStore((s) => s.fetchSkills)

  useEffect(() => {
    if (!expanded) return
    fetchSkills()
  }, [expanded, fetchSkills])

  const activeCount = skills.filter((s) => s.active).length
  const lastFetchError = useSkillStore((s) => s.lastFetchError)
  const prompt = skills.filter((s) => s.category === 'prompt')
  const analysis = skills.filter((s) => s.category === 'analysis')
  const other = skills.filter((s) => s.category !== 'prompt' && s.category !== 'analysis')

  return (
    <div className="border-t border-gray-200 dark:border-gray-800 pt-2 mt-2">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
      >
        <span className="font-medium">⚡ Skills</span>
        <span className="text-xs bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 px-1.5 rounded-full">
          {activeCount}
        </span>
      </button>

      {expanded && (
        <div className="mt-1 max-h-60 overflow-y-auto">
          {lastFetchError && (
            <p className="text-xs text-red-500 dark:text-red-400 px-3 py-2" title={lastFetchError}>
              Skills unavailable ({lastFetchError.slice(0, 80)})
            </p>
          )}
          {loading ? (
            <p className="text-xs text-gray-400 px-3 py-2">Loading skills…</p>
          ) : (
            <>
              {prompt.length > 0 && (
                <div className="mb-1">
                  <span className="px-3 text-[10px] font-medium text-gray-400 uppercase">Prompt</span>
                  {prompt.map((s) => <SkillCard key={s.id} skill={s} />)}
                </div>
              )}
              {analysis.length > 0 && (
                <div className="mb-1">
                  <span className="px-3 text-[10px] font-medium text-gray-400 uppercase">Analysis</span>
                  {analysis.map((s) => <SkillCard key={s.id} skill={s} />)}
                </div>
              )}
              {other.length > 0 && (
                <div className="mb-1">
                  <span className="px-3 text-[10px] font-medium text-gray-400 uppercase">Other</span>
                  {other.map((s) => <SkillCard key={s.id} skill={s} />)}
                </div>
              )}
              {!prompt.length && !analysis.length && !other.length && (
                <p className="text-xs text-gray-400 px-3 py-2">
                  {lastFetchError ? 'Open sidecar and retry expanding Skills.' : 'No skills available'}
                </p>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
