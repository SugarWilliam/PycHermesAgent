import { Children } from 'react'

const CALLOUT_TYPES = {
  NOTE: { bg: 'bg-blue-50 dark:bg-blue-900/20', border: 'border-blue-300 dark:border-blue-700', icon: 'ℹ' },
  TIP: { bg: 'bg-green-50 dark:bg-green-900/20', border: 'border-green-300 dark:border-green-700', icon: '💡' },
  WARNING: { bg: 'bg-amber-50 dark:bg-amber-900/20', border: 'border-amber-300 dark:border-amber-700', icon: '⚠' },
  CAUTION: { bg: 'bg-red-50 dark:bg-red-900/20', border: 'border-red-300 dark:border-red-700', icon: '🔴' },
  IMPORTANT: { bg: 'bg-purple-50 dark:bg-purple-900/20', border: 'border-purple-300 dark:border-purple-700', icon: '❗' }
}

const CITE_RE = /^\[cite:\s*(.+?)\]/

export default function CalloutBlock({ children }) {
  // Extract text content to detect callout type or citation
  const textContent = extractText(children)

  // Check for [!TYPE] pattern
  const calloutMatch = textContent.match(/^\[!(NOTE|TIP|WARNING|CAUTION|IMPORTANT)\]/)
  if (calloutMatch) {
    const type = calloutMatch[1]
    const style = CALLOUT_TYPES[type]
    return (
      <div className={`my-3 rounded-lg border-l-4 ${style.border} ${style.bg} p-3`}>
        <div className="flex items-start gap-2">
          <span>{style.icon}</span>
          <div className="text-sm flex-1">{children}</div>
        </div>
      </div>
    )
  }

  // Check for [cite: source] pattern
  const citeMatch = textContent.match(CITE_RE)
  if (citeMatch) {
    return (
      <div className="my-3 rounded-lg border-l-4 border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800/50 p-3">
        <div className="text-xs text-blue-600 dark:text-blue-400 mb-1 font-medium">
          📎 {citeMatch[1]}
        </div>
        <div className="text-sm">{children}</div>
      </div>
    )
  }

  // Default blockquote
  return (
    <blockquote className="my-3 border-l-4 border-gray-300 dark:border-gray-600 pl-4 italic text-gray-600 dark:text-gray-400">
      {children}
    </blockquote>
  )
}

function extractText(children) {
  let text = ''
  Children.forEach(children, (child) => {
    if (typeof child === 'string') text += child
    else if (child?.props?.children) text += extractText(child.props.children)
  })
  return text.trim()
}
