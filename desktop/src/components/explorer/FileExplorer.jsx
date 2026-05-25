import { useState, useEffect, useCallback } from 'react'

// File extension to icon/color mapping
const EXT_ICONS = {
  md: { icon: 'M', color: 'text-blue-400' },
  py: { icon: 'Py', color: 'text-yellow-400' },
  c: { icon: 'C', color: 'text-blue-300' },
  cpp: { icon: 'C+', color: 'text-blue-300' },
  h: { icon: 'H', color: 'text-purple-400' },
  hpp: { icon: 'H+', color: 'text-purple-400' },
  js: { icon: 'JS', color: 'text-yellow-300' },
  jsx: { icon: 'JX', color: 'text-cyan-400' },
  json: { icon: '{}', color: 'text-yellow-500' },
  txt: { icon: 'T', color: 'text-gray-400' },
  default: { icon: '·', color: 'text-gray-500' },
}

function getFileIcon(name) {
  const ext = name.split('.').pop()?.toLowerCase() || ''
  return EXT_ICONS[ext] || EXT_ICONS.default
}

function TreeNode({ item, depth = 0, onFileOpen }) {
  const [expanded, setExpanded] = useState(false)
  const [children, setChildren] = useState(null)
  const [loading, setLoading] = useState(false)

  const toggle = async () => {
    if (!item.isDirectory) {
      onFileOpen(item.path)
      return
    }
    if (!expanded && children === null) {
      setLoading(true)
      const res = await window.fileSystem.readDir(item.path)
      if (res.ok) setChildren(res.items)
      setLoading(false)
    }
    setExpanded(!expanded)
  }

  const icon = item.isDirectory
    ? (expanded ? '▾' : '▸')
    : null
  const fileIcon = !item.isDirectory ? getFileIcon(item.name) : null

  return (
    <div>
      <button
        onClick={toggle}
        className={`w-full flex items-center gap-1 px-2 py-[3px] text-left text-[13px] hover:bg-gray-700/40 rounded transition-colors`}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
        title={item.path}
      >
        {item.isDirectory ? (
          <span className="w-4 text-center text-gray-400 text-[11px] flex-shrink-0">{icon}</span>
        ) : (
          <span className={`w-4 text-center text-[10px] font-bold flex-shrink-0 ${fileIcon.color}`}>{fileIcon.icon}</span>
        )}
        <span className={`truncate ${item.isDirectory ? 'text-gray-200' : 'text-gray-300'}`}>
          {item.name}
        </span>
        {loading && <span className="text-[10px] text-gray-500 ml-auto">...</span>}
      </button>
      {expanded && children && (
        <div>
          {children.map((child) => (
            <TreeNode key={child.path} item={child} depth={depth + 1} onFileOpen={onFileOpen} />
          ))}
        </div>
      )}
    </div>
  )
}

export default function FileExplorer({ onFileOpen }) {
  const [rootPath, setRootPath] = useState(null)
  const [rootItems, setRootItems] = useState([])
  const [error, setError] = useState(null)

  const openFolder = async () => {
    if (!window.fileSystem?.pickFolder) return
    const result = await window.fileSystem.pickFolder()
    if (result.canceled || !result.filePaths?.length) return
    const dir = result.filePaths[0]
    setRootPath(dir)
    loadDir(dir)
  }

  const loadDir = async (dir) => {
    const res = await window.fileSystem.readDir(dir)
    if (res.ok) {
      setRootItems(res.items)
      setError(null)
    } else {
      setError(res.error)
      setRootItems([])
    }
  }

  // Load last opened folder from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('pyc-explorer-root')
    if (saved) {
      setRootPath(saved)
      loadDir(saved)
    }
  }, [])

  // Save root path when it changes
  useEffect(() => {
    if (rootPath) localStorage.setItem('pyc-explorer-root', rootPath)
  }, [rootPath])

  const folderName = rootPath ? rootPath.split(/[\\/]/).pop() : null

  return (
    <div className="flex flex-col h-full bg-gray-900">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-700/50">
        <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">资源管理器</span>
        <div className="flex gap-1">
          <button
            onClick={openFolder}
            className="p-1 rounded hover:bg-gray-700 text-gray-400 hover:text-gray-200"
            title="打开文件夹"
          >
            <svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M3 5a2 2 0 012-2h3l2 2h5a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V5z" />
            </svg>
          </button>
        </div>
      </div>

      {/* Tree */}
      <div className="flex-1 overflow-y-auto py-1">
        {!rootPath && (
          <div className="px-4 py-8 text-center">
            <p className="text-[12px] text-gray-500 mb-3">没有打开的文件夹</p>
            <button
              onClick={openFolder}
              className="px-3 py-1.5 rounded-md bg-cyan-500/10 text-cyan-400 text-[12px] font-medium hover:bg-cyan-500/20 border border-cyan-500/20"
            >
              打开文件夹
            </button>
          </div>
        )}
        {rootPath && folderName && (
          <div className="px-2 py-1">
            <div className="flex items-center gap-1 text-[12px] font-semibold text-gray-300 px-2 py-1">
              <span className="text-gray-400">▾</span>
              <span className="uppercase truncate">{folderName}</span>
            </div>
          </div>
        )}
        {error && <p className="px-4 text-[11px] text-red-400">{error}</p>}
        {rootItems.map((item) => (
          <TreeNode key={item.path} item={item} depth={1} onFileOpen={onFileOpen} />
        ))}
      </div>
    </div>
  )
}
