import { useState } from 'react'

function Badge({ label, value, color }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${color}`}>
      {label}: {value}
    </span>
  )
}

function CollapsibleList({ title, items }) {
  const [expanded, setExpanded] = useState(items.length <= 3)

  if (!items || items.length === 0) return null

  return (
    <div className="mt-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="text-xs font-medium text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 flex items-center gap-1"
      >
        <span className={`transform transition-transform ${expanded ? 'rotate-90' : ''}`}>▶</span>
        {title} ({items.length})
      </button>
      {expanded && (
        <ul className="mt-1 ml-4 space-y-0.5">
          {items.map((item, i) => (
            <li key={i} className="text-xs text-gray-700 dark:text-gray-300 list-disc">
              {item}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default function AnalysisCard({ data }) {
  if (!data) return null

  return (
    <div className="mt-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 p-3 text-sm">
      <div className="flex items-center justify-between mb-2">
        <span className="font-semibold text-gray-800 dark:text-gray-200 text-xs uppercase tracking-wide">
          Analysis Summary
        </span>
        {data.degraded && (
          <span className="px-1.5 py-0.5 rounded text-xs font-medium bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200">
            Degraded
          </span>
        )}
      </div>

      <div className="flex flex-wrap gap-2 mb-2">
        <Badge label="Method" value={data.method} color="bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200" />
        <Badge label="CE" value={data.evidence_grade} color="bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200" />
        <Badge label="SR" value={data.sr_grade} color="bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200" />
      </div>

      {data.rationale && (
        <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">{data.rationale}</p>
      )}

      <CollapsibleList title="Risks" items={data.risks} />
      <CollapsibleList title="Assumptions" items={data.assumptions} />
    </div>
  )
}
