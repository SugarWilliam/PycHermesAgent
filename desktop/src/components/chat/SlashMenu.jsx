import { useEffect, useRef } from 'react'

export default function SlashMenu({ commands, selectedIndex, onSelect }) {
  const menuRef = useRef(null)

  useEffect(() => {
    if (!menuRef.current) return
    const item = menuRef.current.children[selectedIndex]
    if (item) item.scrollIntoView({ block: 'nearest' })
  }, [selectedIndex])

  if (!commands.length) {
    return (
      <div className="absolute bottom-full left-0 right-0 mb-1 z-50 animate-fade-in">
        <div className="mx-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-lg p-3">
          <p className="text-xs text-gray-400">No matching commands</p>
        </div>
      </div>
    )
  }

  return (
    <div className="absolute bottom-full left-0 right-0 mb-1 z-50 animate-fade-in">
      <div
        ref={menuRef}
        className="mx-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-lg max-h-64 overflow-y-auto"
      >
        <div className="px-3 py-2 border-b border-gray-100 dark:border-gray-700">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Commands</p>
        </div>
        {commands.map((cmd, i) => (
          <button
            key={cmd.name}
            type="button"
            onClick={() => onSelect(cmd)}
            className={`w-full flex items-center gap-3 px-3 py-2 text-left transition-colors ${
              i === selectedIndex
                ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/50'
            }`}
          >
            <span className="text-base">{cmd.icon}</span>
            <span className="flex-1">
              <span className="text-sm font-medium">/{cmd.name}</span>
              <span className="ml-2 text-xs text-gray-400">{cmd.description}</span>
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}
