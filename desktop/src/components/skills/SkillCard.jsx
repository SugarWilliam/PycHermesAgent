import useSkillStore from '../../store/skillStore'

export default function SkillCard({ skill }) {
  const activate = useSkillStore((s) => s.activateSkill)
  const deactivate = useSkillStore((s) => s.deactivateSkill)

  const toggle = () => {
    if (!skill.activatable) return
    skill.active ? deactivate(skill.id) : activate(skill.id)
  }

  return (
    <div className="flex items-start gap-2 px-2 py-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-medium text-gray-800 dark:text-gray-200 truncate">
            {skill.name}
          </span>
          <span className="text-[10px] px-1 rounded bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
            {skill.sourceKind}
          </span>
        </div>
        <p className="text-[11px] text-gray-500 dark:text-gray-400 truncate mt-0.5">
          {skill.description}
        </p>
      </div>
      <button
        onClick={toggle}
        disabled={!skill.activatable}
        className={`mt-0.5 w-8 h-4 rounded-full relative transition-colors flex-shrink-0 ${
          skill.active
            ? 'bg-blue-500'
            : 'bg-gray-300 dark:bg-gray-600'
        } ${!skill.activatable ? 'opacity-40 cursor-not-allowed' : ''}`}
      >
        <span className={`absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform ${
          skill.active ? 'left-4' : 'left-0.5'
        }`} />
      </button>
    </div>
  )
}
