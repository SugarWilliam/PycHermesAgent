import useCitationStore from '../../store/citationStore'

export default function CitationList() {
  const citations = useCitationStore((s) => s.citations)

  if (!citations || citations.length === 0) return null

  // Group by source document
  const grouped = citations.reduce((acc, c) => {
    const key = c.title || c.source_uri || 'Unknown'
    if (!acc[key]) acc[key] = []
    acc[key].push(c)
    return acc
  }, {})

  return (
    <div className="space-y-3">
      {Object.entries(grouped).map(([source, items]) => (
        <div key={source} className="rounded-lg border border-gray-200 dark:border-gray-700 p-2">
          <h5 className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1 truncate" title={source}>
            {source}
          </h5>
          <ul className="space-y-1">
            {items.map((cite, i) => (
              <li
                key={i}
                className="rounded bg-gray-50 dark:bg-gray-800 p-2 cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
                title={cite.snippet}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-600 dark:text-gray-400">
                    {cite.page ? `p.${cite.page}` : cite.source_uri}
                  </span>
                  {cite.relevance != null && (
                    <RelevanceIndicator value={cite.relevance} />
                  )}
                </div>
                {cite.snippet && (
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
                    {cite.snippet}
                  </p>
                )}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  )
}

function RelevanceIndicator({ value }) {
  const pct = Math.round(value * 100)
  const color =
    pct >= 75
      ? 'text-green-600 dark:text-green-400'
      : pct >= 50
        ? 'text-amber-600 dark:text-amber-400'
        : 'text-gray-400 dark:text-gray-500'
  return (
    <span className={`text-[10px] font-mono font-medium ${color}`}>
      {pct}%
    </span>
  )
}
