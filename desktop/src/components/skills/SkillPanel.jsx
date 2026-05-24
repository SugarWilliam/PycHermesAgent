import { useEffect, useState } from 'react'
import useSkillStore from '../../store/skillStore'
import { saveUserSkill } from '../../services/sidecarClient'
import SkillCard from './SkillCard'

export default function SkillPanel({ expanded, onToggle }) {
  const skills = useSkillStore((s) => s.skills)
  const loading = useSkillStore((s) => s.loading)
  const fetchSkills = useSkillStore((s) => s.fetchSkills)
  const [pubId, setPubId] = useState('')
  const [pubMd, setPubMd] = useState('---\nname: user-skill\ndescription: User-authored SKILL\n---\n\n### Scope\n')
  const [pubBusy, setPubBusy] = useState(false)
  const [pubMsg, setPubMsg] = useState('')

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
        <div className="mt-1 max-h-[32rem] overflow-y-auto">
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

          <details className="px-3 py-2 border-t border-gray-100 dark:border-gray-800 mt-1">
            <summary className="text-[11px] text-gray-500 dark:text-gray-400 cursor-pointer select-none">
              发布用户 SKILL 到运行时 (POST /skills/user)
            </summary>
            <form
              className="mt-2 space-y-2"
              onSubmit={async (e) => {
                e.preventDefault()
                const slug = pubId.trim()
                if (!slug) {
                  setPubMsg('填写 skill id（slug）')
                  return
                }
                setPubBusy(true)
                setPubMsg('')
                try {
                  await saveUserSkill(slug, pubMd)
                  setPubMsg('已保存并重载列表')
                  await fetchSkills()
                } catch (err) {
                  setPubMsg(err?.message || String(err))
                } finally {
                  setPubBusy(false)
                }
              }}
            >
              <input
                type="text"
                placeholder="skill_id（slug）"
                value={pubId}
                onChange={(e) => setPubId(e.target.value)}
                className="w-full text-[11px] rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-2 py-1"
              />
              <textarea
                rows={8}
                value={pubMd}
                onChange={(e) => setPubMd(e.target.value)}
                className="w-full text-[11px] font-mono rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-2 py-1"
              />
              <button
                type="submit"
                disabled={pubBusy || loading}
                className="w-full text-xs py-1 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {pubBusy ? '保存中…' : '保存 SKILL.md'}
              </button>
            </form>
            {pubMsg ? <p className="text-[10px] mt-1 text-gray-600 dark:text-gray-300">{pubMsg}</p> : null}
          </details>
        </div>
      )}
    </div>
  )
}
