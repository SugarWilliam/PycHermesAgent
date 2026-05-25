import { useState, useEffect } from 'react'
import useSettingsStore from '../../store/settingsStore'
import { useSidecarStatusStore } from '../../store/sidecarStatusStore'
import { fetchProviders, fetchModels, fetchConfig, listKnowledgeBases, ingestFileToKnowledgeBase, ingestPdfToKnowledgeBase, createKnowledgeBase, fetchSkills } from '../../services/sidecarClient'

// --- Inline SVG Icons (20x20) ---
const IconGear = () => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M10 13a3 3 0 100-6 3 3 0 000 6z" />
    <path d="M16.5 10a6.5 6.5 0 01-.4 2.2l1.6 1.3-1.4 2.4-1.9-.6a6.5 6.5 0 01-1.9 1.1l-.4 2h-2.8l-.4-2a6.5 6.5 0 01-1.9-1.1l-1.9.6-1.4-2.4 1.6-1.3A6.5 6.5 0 013.5 10c0-.8.1-1.5.4-2.2L2.3 6.5l1.4-2.4 1.9.6A6.5 6.5 0 017.5 3.6l.4-2h2.8l.4 2a6.5 6.5 0 011.9 1.1l1.9-.6 1.4 2.4-1.6 1.3c.2.7.3 1.4.3 2.2z" />
  </svg>
)

const IconSparkles = () => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M10 2l1.5 4.5L16 8l-4.5 1.5L10 14l-1.5-4.5L4 8l4.5-1.5L10 2z" />
    <path d="M15 12l.8 2.2L18 15l-2.2.8L15 18l-.8-2.2L12 15l2.2-.8L15 12z" />
  </svg>
)

const IconServer = () => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
    <rect x="3" y="3" width="14" height="5" rx="1.5" />
    <rect x="3" y="12" width="14" height="5" rx="1.5" />
    <circle cx="6" cy="5.5" r="0.75" fill="currentColor" />
    <circle cx="6" cy="14.5" r="0.75" fill="currentColor" />
  </svg>
)

const IconDatabase = () => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
    <ellipse cx="10" cy="5" rx="6" ry="2.5" />
    <path d="M4 5v10c0 1.4 2.7 2.5 6 2.5s6-1.1 6-2.5V5" />
    <path d="M4 10c0 1.4 2.7 2.5 6 2.5s6-1.1 6-2.5" />
  </svg>
)

const IconTerminal = () => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
    <rect x="2" y="3" width="16" height="14" rx="2" />
    <path d="M5 8l3 2.5L5 13" />
    <path d="M10 13h5" />
  </svg>
)

const IconMoon = () => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M17 11.5A7.5 7.5 0 118.5 3 5.5 5.5 0 0017 11.5z" />
  </svg>
)

const IconSun = () => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
    <circle cx="10" cy="10" r="3.5" />
    <path d="M10 2v2M10 16v2M2 10h2M16 10h2M4.9 4.9l1.4 1.4M13.7 13.7l1.4 1.4M4.9 15.1l1.4-1.4M13.7 6.3l1.4-1.4" />
  </svg>
)

const IconMonitor = () => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
    <rect x="2" y="3" width="16" height="11" rx="2" />
    <path d="M7 17h6M10 14v3" />
  </svg>
)

const IconClose = () => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M5 5l10 10M15 5L5 15" />
  </svg>
)

const IconSearch = () => (
  <svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
    <circle cx="9" cy="9" r="5" />
    <path d="M13 13l4 4" />
  </svg>
)

const PROVIDER_ENV_MAP = {
  'github-copilot': 'GITHUB_TOKEN',
  'openrouter': 'OPENROUTER_API_KEY',
  'openai-compatible': 'OPENAI_API_KEY',
  'opencode': 'OPENCODE_API_KEY',
}

const NAV_SECTIONS = [
  { id: 'general', label: '通用', subtitle: '主题、快捷键', Icon: IconGear },
  { id: 'model', label: '模型', subtitle: 'AI模型配置', Icon: IconSparkles },
  { id: 'provider', label: '提供商', subtitle: 'LLM连接管理', Icon: IconServer },
  { id: 'resources', label: '资源', subtitle: '知识库、技能', Icon: IconDatabase },
  { id: 'advanced', label: '高级', subtitle: 'Sidecar引擎', Icon: IconTerminal },
]

export default function SettingsPanel({ open, onClose }) {
  const [activeSection, setActiveSection] = useState('general')
  const [providers, setProviders] = useState([])
  const [models, setModels] = useState([])
  const [knowledgeBases, setKnowledgeBases] = useState([])
  const [skills, setSkills] = useState([])
  const [loading, setLoading] = useState(false)

  const settings = useSettingsStore((s) => s.settings)
  const saveSettings = useSettingsStore((s) => s.saveSettings)
  const sidecarStatus = useSidecarStatusStore((s) => s.status)

  useEffect(() => {
    if (!open) return
    setLoading(true)
    Promise.allSettled([
      fetchProviders(),
      fetchModels(),
      listKnowledgeBases(),
      fetchSkills(),
    ]).then(([prov, mod, kbs, sk]) => {
      if (prov.status === 'fulfilled') setProviders(prov.value?.items || [])
      if (mod.status === 'fulfilled') setModels(mod.value?.items || [])
      if (kbs.status === 'fulfilled') setKnowledgeBases(kbs.value?.items || kbs.value || [])
      if (sk.status === 'fulfilled') setSkills(sk.value?.items || sk.value || [])
    }).finally(() => setLoading(false))
  }, [open])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      {/* Modal */}
      <div className="relative z-10 flex w-full max-w-[900px] h-[80vh] rounded-2xl border border-gray-700/50 bg-gray-950 shadow-2xl overflow-hidden">
        {/* Left sidebar nav */}
        <nav className="w-[200px] flex-shrink-0 bg-gray-900 border-r border-gray-800 py-4 flex flex-col">
          <h2 className="px-5 pb-4 text-sm font-semibold text-gray-300 tracking-wide uppercase">设置</h2>
          <div className="flex-1 space-y-0.5 px-2">
            {NAV_SECTIONS.map(({ id, label, subtitle, Icon }) => (
              <button
                key={id}
                onClick={() => setActiveSection(id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all ${
                  activeSection === id
                    ? 'bg-gradient-to-r from-cyan-500/10 to-transparent border-l-2 border-cyan-500 text-cyan-400'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/60 border-l-2 border-transparent'
                }`}
              >
                <span className="flex-shrink-0"><Icon /></span>
                <div className="min-w-0">
                  <div className="text-sm font-medium truncate">{label}</div>
                  <div className="text-[11px] text-gray-500 truncate">{subtitle}</div>
                </div>
              </button>
            ))}
          </div>
          {/* Close button at bottom */}
          <div className="px-4 pt-4 border-t border-gray-800">
            <button
              onClick={onClose}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm text-gray-400 hover:text-gray-200 hover:bg-gray-800 transition-colors"
            >
              <IconClose />
              <span>关闭</span>
            </button>
          </div>
        </nav>

        {/* Right content area */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeSection === 'general' && <GeneralSection settings={settings} saveSettings={saveSettings} />}
          {activeSection === 'model' && <ModelSection settings={settings} saveSettings={saveSettings} models={models} providers={providers} />}
          {activeSection === 'provider' && <ProviderSection providers={providers} settings={settings} saveSettings={saveSettings} />}
          {activeSection === 'resources' && <ResourcesSection knowledgeBases={knowledgeBases} setKnowledgeBases={setKnowledgeBases} skills={skills} />}
          {activeSection === 'advanced' && <AdvancedSection settings={settings} saveSettings={saveSettings} sidecarStatus={sidecarStatus} />}
        </div>
      </div>
    </div>
  )
}

// ============================================================
// Section: 通用
// ============================================================
function GeneralSection({ settings, saveSettings }) {
  const currentTheme = settings?.theme || 'system'
  const currentAnalysisMode = settings?.defaultAnalysisMode || 'casual'
  const currentSendKey = settings?.sendKey || 'Enter'

  const themes = [
    { id: 'dark', label: '深色', Icon: IconMoon },
    { id: 'light', label: '浅色', Icon: IconSun },
    { id: 'system', label: '跟随系统', Icon: IconMonitor },
  ]

  const analysisModes = [
    { id: 'casual', label: '随意', desc: '快速回答，最少约束' },
    { id: 'structured', label: '结构化', desc: '带方法与证据引用' },
    { id: 'formal', label: '正式', desc: '完整方法论、风险评估' },
  ]

  return (
    <div className="space-y-8">
      <SectionTitle title="通用设置" />

      {/* Theme */}
      <FieldGroup label="主题">
        <div className="grid grid-cols-3 gap-3">
          {themes.map(({ id, label, Icon }) => (
            <button
              key={id}
              onClick={() => saveSettings({ ...settings, theme: id })}
              className={`flex flex-col items-center gap-2 p-4 rounded-xl border transition-all ${
                currentTheme === id
                  ? 'border-cyan-500 bg-cyan-500/5 text-cyan-400'
                  : 'border-gray-700/50 bg-gray-800/50 text-gray-400 hover:border-cyan-500/30 hover:text-gray-200'
              }`}
            >
              <Icon />
              <span className="text-xs font-medium">{label}</span>
            </button>
          ))}
        </div>
      </FieldGroup>

      {/* Analysis Mode */}
      <FieldGroup label="分析模式">
        <div className="grid grid-cols-3 gap-3">
          {analysisModes.map(({ id, label, desc }) => (
            <button
              key={id}
              onClick={() => saveSettings({ ...settings, defaultAnalysisMode: id })}
              className={`flex flex-col items-start p-4 rounded-xl border transition-all text-left ${
                currentAnalysisMode === id
                  ? 'border-cyan-500 bg-cyan-500/5'
                  : 'border-gray-700/50 bg-gray-800/50 hover:border-cyan-500/30'
              }`}
            >
              <span className={`text-sm font-medium ${currentAnalysisMode === id ? 'text-cyan-400' : 'text-gray-200'}`}>{label}</span>
              <span className="text-[11px] text-gray-500 mt-1">{desc}</span>
            </button>
          ))}
        </div>
      </FieldGroup>

      {/* Send Key */}
      <FieldGroup label="发送快捷键">
        <select
          value={currentSendKey}
          onChange={(e) => saveSettings({ ...settings, sendKey: e.target.value })}
          className="w-48 px-3 py-2 rounded-lg border border-gray-700/50 bg-gray-800 text-sm text-gray-200 focus:outline-none focus:border-cyan-500/50"
        >
          <option value="Enter">Enter</option>
          <option value="Ctrl+Enter">Ctrl+Enter</option>
        </select>
      </FieldGroup>
    </div>
  )
}

// ============================================================
// Section: 模型
// ============================================================
function ModelSection({ settings, saveSettings, models, providers }) {
  const [search, setSearch] = useState('')
  const [showSelector, setShowSelector] = useState(false)
  const [customModel, setCustomModel] = useState('')

  const currentModel = settings?.defaultModel || ''

  const filteredModels = models.filter((m) =>
    m.name?.toLowerCase().includes(search.toLowerCase()) ||
    m.id?.toLowerCase().includes(search.toLowerCase())
  )

  const groupedByProvider = filteredModels.reduce((acc, m) => {
    const pId = m.provider_id || 'other'
    if (!acc[pId]) acc[pId] = []
    acc[pId].push(m)
    return acc
  }, {})

  const providerName = (id) => providers.find((p) => p.id === id)?.name || id

  const selectModel = (modelId) => {
    saveSettings({ ...settings, defaultModel: modelId })
    setShowSelector(false)
  }

  return (
    <div className="space-y-8">
      <SectionTitle title="模型配置" />

      {/* Current model */}
      <FieldGroup label="当前模型">
        <div className="flex items-center gap-3">
          <div className="flex-1 px-4 py-3 rounded-xl border border-gray-700/50 bg-gray-800/50 text-sm text-gray-200 truncate">
            {currentModel || '未设置'}
          </div>
          <button
            onClick={() => setShowSelector(!showSelector)}
            className="px-4 py-2.5 rounded-lg bg-cyan-500/10 text-cyan-400 text-sm font-medium hover:bg-cyan-500/20 transition-colors border border-cyan-500/20"
          >
            更换
          </button>
        </div>
      </FieldGroup>

      {/* Model selector */}
      {showSelector && (
        <div className="rounded-xl border border-gray-700/50 bg-gray-800/30 overflow-hidden">
          {/* Search */}
          <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-700/50">
            <IconSearch />
            <input
              type="text"
              placeholder="搜索模型..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="flex-1 bg-transparent text-sm text-gray-200 placeholder-gray-500 focus:outline-none"
            />
          </div>
          {/* Grouped list */}
          <div className="max-h-[300px] overflow-y-auto divide-y divide-gray-700/30">
            {Object.entries(groupedByProvider).map(([pId, pModels]) => (
              <div key={pId}>
                <div className="px-4 py-2 text-[11px] font-semibold text-gray-500 uppercase bg-gray-900/50 sticky top-0">
                  {providerName(pId)}
                </div>
                {pModels.map((m) => (
                  <button
                    key={m.id}
                    onClick={() => selectModel(m.id)}
                    className={`w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-gray-700/30 transition-colors ${
                      currentModel === m.id ? 'bg-cyan-500/5' : ''
                    }`}
                  >
                    <span className={`flex-1 text-sm truncate ${currentModel === m.id ? 'text-cyan-400' : 'text-gray-200'}`}>
                      {m.name || m.id}
                    </span>
                    <div className="flex gap-1.5 flex-shrink-0">
                      {m.free && <Tag label="free" color="green" />}
                      {m.supports_tools && <Tag label="tools" color="purple" />}
                      {m.tags?.includes('reasoning') && <Tag label="reasoning" color="amber" />}
                      {m.tags?.includes('fast') && <Tag label="fast" color="sky" />}
                    </div>
                  </button>
                ))}
              </div>
            ))}
            {Object.keys(groupedByProvider).length === 0 && (
              <div className="px-4 py-6 text-sm text-gray-500 text-center">无匹配模型</div>
            )}
          </div>
        </div>
      )}

      {/* Custom model input */}
      <FieldGroup label="自定义模型">
        <div className="flex items-center gap-3">
          <input
            type="text"
            placeholder="provider/model-name"
            value={customModel}
            onChange={(e) => setCustomModel(e.target.value)}
            className="flex-1 px-4 py-2.5 rounded-lg border border-gray-700/50 bg-gray-800/50 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-cyan-500/50"
          />
          <button
            onClick={() => { if (customModel.trim()) { selectModel(customModel.trim()); setCustomModel('') } }}
            className="px-4 py-2.5 rounded-lg bg-gray-700/50 text-sm text-gray-300 hover:bg-gray-700 transition-colors"
          >
            应用
          </button>
        </div>
        <p className="text-[11px] text-gray-500 mt-1.5">输入任意 provider/model 标识符</p>
      </FieldGroup>
    </div>
  )
}

// ============================================================
// Section: 提供商
// ============================================================
function ProviderSection({ providers, settings, saveSettings }) {
  const [expandedProvider, setExpandedProvider] = useState(null)
  const [apiKeyInput, setApiKeyInput] = useState('')
  const [connectingId, setConnectingId] = useState(null)

  // GitHub Device Code flow state
  const [deviceCodeState, setDeviceCodeState] = useState(null) // null | { user_code, verification_uri, device_code, interval, status }

  const connectedProviders = providers.filter((p) => {
    const envKey = PROVIDER_ENV_MAP[p.id]
    return envKey && settings?.[envKey]
  })

  const availableProviders = providers.filter((p) => {
    const envKey = PROVIDER_ENV_MAP[p.id]
    return !envKey || !settings?.[envKey]
  })

  const handleConnect = async (provider) => {
    const envKey = PROVIDER_ENV_MAP[provider.id]
    if (!envKey || !apiKeyInput.trim()) return
    setConnectingId(provider.id)
    try {
      if (window.desktopHost?.setProviderEnv) {
        await window.desktopHost.setProviderEnv({ [envKey]: apiKeyInput.trim() })
      }
      saveSettings({ ...settings, [envKey]: apiKeyInput.trim(), provider: provider.id })
      setApiKeyInput('')
      setExpandedProvider(null)
    } finally {
      setConnectingId(null)
    }
  }

  const handleDisconnect = async (provider) => {
    const envKey = PROVIDER_ENV_MAP[provider.id]
    if (!envKey) return
    if (window.desktopHost?.setProviderEnv) {
      await window.desktopHost.setProviderEnv({ [envKey]: '' })
    }
    // Set to empty string so it overrides the current value during merge
    const next = { ...settings, [envKey]: '' }
    if (next.provider === provider.id) next.provider = ''
    saveSettings(next)
  }

  // GitHub Device Code Flow
  const startDeviceCodeFlow = async () => {
    if (!window.desktopHost?.githubDeviceCodeStart) return
    setDeviceCodeState({ status: 'requesting' })
    const result = await window.desktopHost.githubDeviceCodeStart()
    if (!result.ok) {
      setDeviceCodeState({ status: 'error', error: result.error })
      return
    }
    setDeviceCodeState({
      status: 'waiting_for_user',
      user_code: result.user_code,
      verification_uri: result.verification_uri,
      device_code: result.device_code,
      interval: result.interval || 5,
    })
    // Auto-open browser
    if (window.desktopHost?.openExternal) {
      window.desktopHost.openExternal(result.verification_uri)
    }
    // Start polling
    pollDeviceCode(result.device_code, (result.interval || 5) * 1000)
  }

  const pollDeviceCode = async (deviceCode, intervalMs) => {
    let attempts = 0
    const maxAttempts = 120 // ~10 minutes at 5s interval
    const poll = async () => {
      if (attempts >= maxAttempts) {
        setDeviceCodeState((prev) => prev && { ...prev, status: 'error', error: '认证超时，请重试' })
        return
      }
      attempts++
      const result = await window.desktopHost.githubDeviceCodePoll(deviceCode)
      if (result.ok) {
        // Success! Token already saved to provider-env.json by main process.
        setDeviceCodeState({ status: 'success' })
        // Update local settings state (use fresh getter to avoid stale closure)
        saveSettings({ GITHUB_TOKEN: result.token, provider: 'github-copilot' })
        setTimeout(() => {
          setDeviceCodeState(null)
          setExpandedProvider(null)
        }, 2000)
        return
      }
      if (result.status === 'pending' || result.status === 'slow_down') {
        const delay = result.status === 'slow_down' ? intervalMs + 5000 : intervalMs
        setTimeout(poll, delay)
        return
      }
      // Error or expired
      setDeviceCodeState((prev) => prev && { ...prev, status: 'error', error: result.error || '认证失败' })
    }
    setTimeout(poll, intervalMs)
  }

  const cancelDeviceCodeFlow = () => {
    setDeviceCodeState(null)
  }

  return (
    <div className="space-y-8">
      <SectionTitle title="提供商管理" />

      {/* Connected */}
      {connectedProviders.length > 0 && (
        <FieldGroup label="已连接">
          <div className="space-y-2">
            {connectedProviders.map((p) => (
              <div key={p.id} className="flex items-center justify-between px-4 py-3 rounded-xl border border-gray-700/50 bg-gray-800/30">
                <div className="flex items-center gap-3">
                  <span className="w-2 h-2 rounded-full bg-green-400" />
                  <span className="text-sm text-gray-200">{p.name}</span>
                </div>
                <button
                  onClick={() => handleDisconnect(p)}
                  className="px-3 py-1.5 rounded-md text-xs text-red-400 hover:bg-red-500/10 transition-colors"
                >
                  断开
                </button>
              </div>
            ))}
          </div>
        </FieldGroup>
      )}

      {/* Available */}
      <FieldGroup label="可用提供商">
        <div className="space-y-2">
          {availableProviders.map((p) => (
            <div key={p.id} className="rounded-xl border border-gray-700/50 bg-gray-800/30 overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3">
                <div>
                  <div className="text-sm text-gray-200">{p.name}</div>
                  <div className="text-[11px] text-gray-500">
                    {p.id === 'github-copilot' ? 'Device Code 认证' : `需要 API Key (${PROVIDER_ENV_MAP[p.id] || 'N/A'})`}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-gray-600" />
                  <button
                    onClick={() => { setExpandedProvider(expandedProvider === p.id ? null : p.id); setApiKeyInput(''); setDeviceCodeState(null) }}
                    className="px-3 py-1.5 rounded-md text-xs text-cyan-400 hover:bg-cyan-500/10 border border-cyan-500/20 transition-colors"
                  >
                    连接
                  </button>
                </div>
              </div>
              {/* Expanded form */}
              {expandedProvider === p.id && (
                <div className="px-4 pb-4 pt-1 border-t border-gray-700/30">
                  {p.id === 'github-copilot' ? (
                    <GitHubDeviceCodePanel
                      state={deviceCodeState}
                      onStart={startDeviceCodeFlow}
                      onCancel={cancelDeviceCodeFlow}
                    />
                  ) : (
                    <div className="flex items-center gap-2 mt-2">
                      <input
                        type="password"
                        placeholder={`输入 ${PROVIDER_ENV_MAP[p.id] || 'API Key'}...`}
                        value={apiKeyInput}
                        onChange={(e) => setApiKeyInput(e.target.value)}
                        className="flex-1 px-3 py-2 rounded-lg border border-gray-700/50 bg-gray-900 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-cyan-500/50"
                      />
                      <button
                        onClick={() => handleConnect(p)}
                        disabled={!apiKeyInput.trim() || connectingId === p.id}
                        className="px-4 py-2 rounded-lg bg-cyan-500/20 text-cyan-400 text-sm font-medium hover:bg-cyan-500/30 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        {connectingId === p.id ? '连接中...' : '确认'}
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
          {availableProviders.length === 0 && providers.length > 0 && (
            <p className="text-sm text-gray-500 text-center py-4">所有提供商已连接</p>
          )}
          {providers.length === 0 && (
            <p className="text-sm text-gray-500 text-center py-4">加载中...</p>
          )}
        </div>
      </FieldGroup>
    </div>
  )
}

// ============================================================
// GitHub Device Code Flow UI Component
// ============================================================
function GitHubDeviceCodePanel({ state, onStart, onCancel }) {
  if (!state) {
    return (
      <div className="mt-2 space-y-3">
        <p className="text-xs text-gray-400">
          使用 GitHub 账号通过 Device Code 流程认证。点击下方按钮将自动打开浏览器完成授权。
        </p>
        <button
          onClick={onStart}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-gray-900 border border-cyan-500/30 text-cyan-400 text-sm font-medium hover:bg-cyan-500/10 hover:border-cyan-500/50 transition-all"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path fillRule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
          </svg>
          使用 GitHub 账号登录
        </button>
      </div>
    )
  }

  if (state.status === 'requesting') {
    return (
      <div className="mt-2 flex items-center gap-2 text-sm text-gray-400">
        <Spinner /> 正在获取验证码...
      </div>
    )
  }

  if (state.status === 'waiting_for_user') {
    return (
      <div className="mt-2 space-y-4">
        {/* User code display */}
        <div className="p-4 rounded-xl bg-gray-900 border border-cyan-500/20 text-center">
          <p className="text-xs text-gray-400 mb-2">请在浏览器中输入以下验证码</p>
          <div className="text-2xl font-mono font-bold tracking-[0.3em] text-cyan-400 select-all">
            {state.user_code}
          </div>
        </div>

        {/* Verification link */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => window.desktopHost?.openExternal?.(state.verification_uri)}
            className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-cyan-500/10 text-cyan-400 text-xs hover:bg-cyan-500/20 transition-colors border border-cyan-500/20"
          >
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M5 1H2a1 1 0 00-1 1v8a1 1 0 001 1h8a1 1 0 001-1V7M7 1h4v4M11 1L5 7" />
            </svg>
            打开 {state.verification_uri}
          </button>
        </div>

        {/* Polling status */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <Spinner /> 等待浏览器中完成授权...
          </div>
          <button
            onClick={onCancel}
            className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
          >
            取消
          </button>
        </div>
      </div>
    )
  }

  if (state.status === 'success') {
    return (
      <div className="mt-2 flex items-center gap-2 text-sm text-green-400">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M3 8.5l3.5 3.5 6.5-7" />
        </svg>
        认证成功！
      </div>
    )
  }

  if (state.status === 'error') {
    return (
      <div className="mt-2 space-y-3">
        <div className="flex items-center gap-2 text-sm text-red-400">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="8" cy="8" r="6" />
            <path d="M8 5v3M8 10.5v.5" />
          </svg>
          {state.error || '认证失败'}
        </div>
        <button
          onClick={onStart}
          className="px-4 py-2 rounded-lg bg-gray-800 text-sm text-gray-300 hover:bg-gray-700 transition-colors"
        >
          重试
        </button>
      </div>
    )
  }

  return null
}

function Spinner() {
  return (
    <svg className="animate-spin" width="14" height="14" viewBox="0 0 14 14" fill="none">
      <circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.5" strokeDasharray="20 12" />
    </svg>
  )
}

// ============================================================
// Section: 资源
// ============================================================
function ResourcesSection({ knowledgeBases, setKnowledgeBases, skills }) {
  const [importing, setImporting] = useState(false)

  const handleImportFiles = async () => {
    if (!window.desktopHost?.pickFiles) return
    setImporting(true)
    try {
      const result = await window.desktopHost.pickFiles({ multiple: true })
      if (result.canceled || !result.filePaths?.length) return

      // Use first knowledge base or create one
      let kbId
      if (knowledgeBases.length > 0) {
        kbId = knowledgeBases[0].id
      } else {
        const newKb = await createKnowledgeBase({ name: '默认知识库' })
        kbId = newKb?.id
        if (kbId) setKnowledgeBases((prev) => [...prev, newKb])
      }
      if (!kbId) return

      for (const filePath of result.filePaths) {
        const isPdf = filePath.toLowerCase().endsWith('.pdf')
        if (isPdf) {
          await ingestPdfToKnowledgeBase(kbId, filePath)
        } else {
          await ingestFileToKnowledgeBase(kbId, filePath)
        }
      }
      // Refresh
      const updated = await listKnowledgeBases()
      setKnowledgeBases(updated?.items || updated || [])
    } finally {
      setImporting(false)
    }
  }

  return (
    <div className="space-y-8">
      <SectionTitle title="资源管理" />

      {/* Knowledge bases */}
      <FieldGroup label="知识库">
        <div className="space-y-2">
          {knowledgeBases.map((kb) => (
            <div key={kb.id} className="flex items-center justify-between px-4 py-3 rounded-xl border border-gray-700/50 bg-gray-800/30">
              <div>
                <div className="text-sm text-gray-200">{kb.name || kb.id}</div>
                <div className="text-[11px] text-gray-500">{kb.document_count ?? '?'} 文档 · {kb.chunk_count ?? '?'} 块</div>
              </div>
            </div>
          ))}
          {knowledgeBases.length === 0 && (
            <p className="text-sm text-gray-500 text-center py-3">暂无知识库</p>
          )}
        </div>
        <button
          onClick={handleImportFiles}
          disabled={importing}
          className="mt-3 px-4 py-2.5 rounded-lg bg-cyan-500/10 text-cyan-400 text-sm font-medium hover:bg-cyan-500/20 transition-colors border border-cyan-500/20 disabled:opacity-40"
        >
          {importing ? '导入中...' : '导入文件'}
        </button>
      </FieldGroup>

      {/* Skills */}
      <FieldGroup label="技能">
        <div className="space-y-2">
          {skills.map((sk, i) => (
            <div key={sk.id || i} className="flex items-center gap-3 px-4 py-3 rounded-xl border border-gray-700/50 bg-gray-800/30">
              <span className="w-2 h-2 rounded-full bg-purple-400 flex-shrink-0" />
              <div className="min-w-0">
                <div className="text-sm text-gray-200 truncate">{sk.name || sk.id}</div>
                {sk.description && <div className="text-[11px] text-gray-500 truncate">{sk.description}</div>}
              </div>
            </div>
          ))}
          {skills.length === 0 && (
            <p className="text-sm text-gray-500 text-center py-3">暂无技能</p>
          )}
        </div>
      </FieldGroup>
    </div>
  )
}

// ============================================================
// Section: 高级
// ============================================================
function AdvancedSection({ settings, saveSettings, sidecarStatus }) {
  const [sidecarUrl, setSidecarUrl] = useState(settings?.sidecarUrl || '')
  const [sidecarCommand, setSidecarCommand] = useState(settings?.sidecarCommand || '')
  const [sidecarArgs, setSidecarArgs] = useState(settings?.sidecarArgs || '')
  const [restarting, setRestarting] = useState(false)

  const handleRestart = async () => {
    setRestarting(true)
    try {
      if (window.sidecar?.restart) {
        await window.sidecar.restart()
      }
    } finally {
      setTimeout(() => setRestarting(false), 2000)
    }
  }

  const handleSave = () => {
    saveSettings({
      ...settings,
      sidecarUrl: sidecarUrl || undefined,
      sidecarCommand: sidecarCommand || undefined,
      sidecarArgs: sidecarArgs || undefined,
    })
  }

  return (
    <div className="space-y-8">
      <SectionTitle title="高级设置" />

      {/* Connection info */}
      <FieldGroup label="Sidecar 状态">
        <div className="px-4 py-3 rounded-xl border border-gray-700/50 bg-gray-800/30 space-y-2">
          <InfoRow label="状态" value={sidecarStatus?.state || 'unknown'} />
          <InfoRow label="URL" value={sidecarStatus?.url || '未解析'} />
          <InfoRow label="来源" value={sidecarStatus?.source || '-'} />
        </div>
      </FieldGroup>

      {/* Overrides */}
      <FieldGroup label="Sidecar URL 覆写">
        <input
          type="text"
          placeholder="http://127.0.0.1:9810"
          value={sidecarUrl}
          onChange={(e) => setSidecarUrl(e.target.value)}
          className="w-full px-4 py-2.5 rounded-lg border border-gray-700/50 bg-gray-800/50 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-cyan-500/50"
        />
      </FieldGroup>

      <FieldGroup label="启动命令覆写">
        <input
          type="text"
          placeholder="python -m pyc_hermes_agent.sidecar_api"
          value={sidecarCommand}
          onChange={(e) => setSidecarCommand(e.target.value)}
          className="w-full px-4 py-2.5 rounded-lg border border-gray-700/50 bg-gray-800/50 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-cyan-500/50"
        />
      </FieldGroup>

      <FieldGroup label="启动参数">
        <input
          type="text"
          placeholder="--host 0.0.0.0 --port 9810"
          value={sidecarArgs}
          onChange={(e) => setSidecarArgs(e.target.value)}
          className="w-full px-4 py-2.5 rounded-lg border border-gray-700/50 bg-gray-800/50 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-cyan-500/50"
        />
      </FieldGroup>

      <div className="flex items-center gap-3">
        <button
          onClick={handleSave}
          className="px-4 py-2.5 rounded-lg bg-gray-700/50 text-sm text-gray-300 hover:bg-gray-700 transition-colors"
        >
          保存配置
        </button>
        <button
          onClick={handleRestart}
          disabled={restarting}
          className="px-4 py-2.5 rounded-lg bg-cyan-500/10 text-cyan-400 text-sm font-medium hover:bg-cyan-500/20 transition-colors border border-cyan-500/20 disabled:opacity-40"
        >
          {restarting ? '重启中...' : '重启 Sidecar'}
        </button>
      </div>
    </div>
  )
}

// ============================================================
// Shared components
// ============================================================
function SectionTitle({ title }) {
  return <h3 className="text-lg font-semibold text-gray-100">{title}</h3>
}

function FieldGroup({ label, children }) {
  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-300">{label}</label>
      {children}
    </div>
  )
}

function Tag({ label, color }) {
  const colors = {
    green: 'bg-green-500/10 text-green-400 border-green-500/20',
    purple: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
    amber: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    sky: 'bg-sky-500/10 text-sky-400 border-sky-500/20',
  }
  return (
    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium border ${colors[color] || colors.sky}`}>
      {label}
    </span>
  )
}

function InfoRow({ label, value }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-gray-400">{label}</span>
      <span className="text-gray-200 font-mono text-xs">{value}</span>
    </div>
  )
}
