/**
 * OpenCode-style model selector popup.
 *
 * Features:
 * - Search bar
 * - Models grouped by provider
 * - Free badge
 * - Tool/reasoning/fast tags
 * - Checkmark on selected model
 * - Click-outside to close
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import useModelStore from '../../store/modelStore'

// ─── Icons ──────────────────────────────────────────────────────────────────────

function SearchIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-gray-500">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-cyan-400">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  )
}

function SettingsIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-gray-500 hover:text-gray-300">
      <line x1="4" y1="21" x2="4" y2="14" /><line x1="4" y1="10" x2="4" y2="3" />
      <line x1="12" y1="21" x2="12" y2="12" /><line x1="12" y1="8" x2="12" y2="3" />
      <line x1="20" y1="21" x2="20" y2="16" /><line x1="20" y1="12" x2="20" y2="3" />
      <line x1="1" y1="14" x2="7" y2="14" />
      <line x1="9" y1="8" x2="15" y2="8" />
      <line x1="17" y1="16" x2="23" y2="16" />
    </svg>
  )
}

// ─── Tag badge ──────────────────────────────────────────────────────────────────

const TAG_COLORS = {
  free: 'bg-green-500/15 text-green-400 border-green-500/30',
  tools: 'bg-purple-500/15 text-purple-400 border-purple-500/30',
  reasoning: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  fast: 'bg-sky-500/15 text-sky-400 border-sky-500/30'
}

function Tag({ label }) {
  const color = TAG_COLORS[label] || 'bg-gray-500/15 text-gray-400 border-gray-500/30'
  return (
    <span className={`inline-flex items-center px-1.5 py-0 rounded text-[10px] font-medium border ${color}`}>
      {label === 'free' ? '\u514D\u8D39' : label}
    </span>
  )
}

// ─── Provider icon (small colored dot) ──────────────────────────────────────────

const PROVIDER_COLORS = {
  'github-copilot': 'bg-blue-400',
  'opencode': 'bg-emerald-400',
  'openrouter': 'bg-orange-400',
  'openai-compatible': 'bg-gray-400',
  'ollama': 'bg-violet-400',
  'lmstudio': 'bg-pink-400'
}

function ProviderDot({ providerId }) {
  const color = PROVIDER_COLORS[providerId] || 'bg-gray-500'
  return <span className={`inline-block w-2 h-2 rounded-full ${color} flex-shrink-0`} />
}

// ─── Main component ─────────────────────────────────────────────────────────────

/**
 * @param {object} props
 * @param {boolean} props.open - whether the popup is visible
 * @param {function} props.onClose - called when user clicks outside or selects a model
 * @param {string} props.currentModel - currently selected model id
 * @param {function} props.onSelect - called with model id when user picks a model
 * @param {'above'|'below'} [props.position='above'] - popup direction relative to trigger
 */
export default function ModelSelector({ open, onClose, currentModel, onSelect, position = 'above' }) {
  const [search, setSearch] = useState('')
  const popupRef = useRef(null)
  const searchInputRef = useRef(null)

  const models = useModelStore((s) => s.models)
  const loading = useModelStore((s) => s.loading)
  const fetchCatalog = useModelStore((s) => s.fetchCatalog)
  const getProviderName = useModelStore((s) => s.getProviderName)

  // Fetch catalog when opened
  useEffect(() => {
    if (open) {
      fetchCatalog()
      // Focus search input
      setTimeout(() => searchInputRef.current?.focus(), 50)
    } else {
      setSearch('')
    }
  }, [open, fetchCatalog])

  // Click-outside handler
  useEffect(() => {
    if (!open) return
    function handleClick(e) {
      if (popupRef.current && !popupRef.current.contains(e.target)) {
        onClose()
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open, onClose])

  // Keyboard: Escape to close
  useEffect(() => {
    if (!open) return
    function handleKey(e) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [open, onClose])

  const handleSelect = useCallback((modelId) => {
    onSelect(modelId)
    onClose()
  }, [onSelect, onClose])

  if (!open) return null

  // Filter
  const filtered = models.filter((m) =>
    m.name?.toLowerCase().includes(search.toLowerCase()) ||
    m.id?.toLowerCase().includes(search.toLowerCase()) ||
    m.provider_id?.toLowerCase().includes(search.toLowerCase())
  )

  // Group by provider
  const grouped = filtered.reduce((acc, m) => {
    const pId = m.provider_id || 'other'
    if (!acc[pId]) acc[pId] = []
    acc[pId].push(m)
    return acc
  }, {})

  // Sort providers: put the provider of current model first, then alphabetical
  const currentProvider = currentModel ? currentModel.split('/')[0] : ''
  const providerOrder = Object.keys(grouped).sort((a, b) => {
    if (a === currentProvider) return -1
    if (b === currentProvider) return 1
    return a.localeCompare(b)
  })

  const posClass = position === 'above'
    ? 'bottom-full mb-2'
    : 'top-full mt-2'

  return (
    <div
      ref={popupRef}
      className={`absolute right-0 ${posClass} z-[100] w-[320px] rounded-xl border border-gray-700/60 bg-gray-900 shadow-2xl overflow-hidden`}
      style={{ backdropFilter: 'blur(12px)' }}
    >
      {/* Header with search */}
      <div className="flex items-center gap-2 px-3 py-2.5 border-b border-gray-700/50">
        <SearchIcon />
        <input
          ref={searchInputRef}
          type="text"
          placeholder="\u641C\u7D22\u6A21\u578B"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 bg-transparent text-sm text-gray-200 placeholder-gray-500 focus:outline-none"
        />
        <button
          type="button"
          title="\u6A21\u578B\u8BBE\u7F6E"
          className="p-1 rounded hover:bg-gray-800 transition-colors"
        >
          <SettingsIcon />
        </button>
      </div>

      {/* Model list */}
      <div className="max-h-[360px] overflow-y-auto overscroll-contain">
        {loading && models.length === 0 && (
          <div className="px-4 py-6 text-sm text-gray-500 text-center">
            \u52A0\u8F7D\u4E2D...
          </div>
        )}

        {providerOrder.map((pId) => (
          <div key={pId}>
            {/* Provider header */}
            <div className="flex items-center gap-2 px-3 py-2 bg-gray-900/80 sticky top-0 z-10 border-b border-gray-800/50">
              <ProviderDot providerId={pId} />
              <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wide">
                {getProviderName(pId)}
              </span>
            </div>

            {/* Models in this provider */}
            {grouped[pId].map((m) => {
              const isSelected = currentModel === m.id
              return (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => handleSelect(m.id)}
                  className={`w-full flex items-center gap-2.5 px-3 py-2 text-left transition-colors ${
                    isSelected
                      ? 'bg-cyan-500/8'
                      : 'hover:bg-gray-800/60'
                  }`}
                >
                  {/* Model name */}
                  <span className={`flex-1 text-[13px] truncate ${
                    isSelected ? 'text-cyan-300 font-medium' : 'text-gray-200'
                  }`}>
                    {m.name || m.model_id || m.id}
                  </span>

                  {/* Tags */}
                  <div className="flex items-center gap-1 flex-shrink-0">
                    {m.free && <Tag label="free" />}
                    {m.supports_tools && <Tag label="tools" />}
                    {m.supports_reasoning && <Tag label="reasoning" />}
                    {m.tags?.includes('fast') && <Tag label="fast" />}
                  </div>

                  {/* Checkmark */}
                  {isSelected && (
                    <span className="flex-shrink-0 ml-1">
                      <CheckIcon />
                    </span>
                  )}
                </button>
              )
            })}
          </div>
        ))}

        {!loading && providerOrder.length === 0 && (
          <div className="px-4 py-6 text-sm text-gray-500 text-center">
            \u65E0\u5339\u914D\u6A21\u578B
          </div>
        )}
      </div>

      {/* Footer hint */}
      <div className="px-3 py-2 border-t border-gray-800/50 flex items-center justify-between">
        <span className="text-[10px] text-gray-500">
          {models.length} \u4E2A\u6A21\u578B\u53EF\u7528
        </span>
        <span className="text-[10px] text-gray-600">
          Esc \u5173\u95ED
        </span>
      </div>
    </div>
  )
}
