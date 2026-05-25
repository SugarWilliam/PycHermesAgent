import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

// Shiki will be loaded dynamically
let shikiHighlighter = null
let shikiLoading = false
const shikiCallbacks = []

async function getHighlighter() {
  if (shikiHighlighter) return shikiHighlighter
  if (shikiLoading) {
    return new Promise(resolve => shikiCallbacks.push(resolve))
  }
  shikiLoading = true
  try {
    const { createHighlighter } = await import('shiki')
    shikiHighlighter = await createHighlighter({
      themes: ['github-dark'],
      langs: ['c', 'cpp', 'python', 'javascript', 'typescript', 'json', 'markdown', 'bash', 'html', 'css'],
    })
    shikiCallbacks.forEach(cb => cb(shikiHighlighter))
    shikiCallbacks.length = 0
    return shikiHighlighter
  } catch (err) {
    console.error('Shiki load failed:', err)
    shikiLoading = false
    return null
  }
}

const LANG_MAP = {
  c: 'c', h: 'c',
  cpp: 'cpp', cc: 'cpp', cxx: 'cpp', hpp: 'cpp', hxx: 'cpp',
  py: 'python',
  js: 'javascript', jsx: 'javascript', mjs: 'javascript',
  ts: 'typescript', tsx: 'typescript',
  json: 'json', jsonc: 'json',
  md: 'markdown',
  sh: 'bash', bash: 'bash',
  html: 'html', htm: 'html',
  css: 'css',
}

function getLanguage(filePath) {
  const ext = filePath.split('.').pop()?.toLowerCase() || ''
  return LANG_MAP[ext] || null
}

function isMarkdown(filePath) {
  const name = filePath.split(/[\\/]/).pop() || ''
  return /\.(md|markdown)$/i.test(name)
}

// Custom markdown styles (since @tailwindcss/typography is not installed)
const mdStyles = `
.md-render h1 { font-size: 1.8em; font-weight: 700; color: #e2e8f0; margin: 1.2em 0 0.6em; padding-bottom: 0.3em; border-bottom: 1px solid #334155; }
.md-render h2 { font-size: 1.4em; font-weight: 600; color: #e2e8f0; margin: 1em 0 0.5em; padding-bottom: 0.2em; border-bottom: 1px solid #1e293b; }
.md-render h3 { font-size: 1.2em; font-weight: 600; color: #cbd5e1; margin: 0.8em 0 0.4em; }
.md-render h4 { font-size: 1.05em; font-weight: 600; color: #cbd5e1; margin: 0.6em 0 0.3em; }
.md-render p { color: #cbd5e1; margin: 0.5em 0; line-height: 1.7; }
.md-render ul, .md-render ol { color: #cbd5e1; margin: 0.5em 0; padding-left: 1.5em; }
.md-render li { margin: 0.25em 0; line-height: 1.6; }
.md-render ul li { list-style-type: disc; }
.md-render ol li { list-style-type: decimal; }
.md-render code { background: #1e293b; color: #f472b6; padding: 0.15em 0.4em; border-radius: 4px; font-size: 0.9em; }
.md-render pre { background: #0f172a; border: 1px solid #334155; border-radius: 6px; padding: 1em; margin: 0.8em 0; overflow-x: auto; }
.md-render pre code { background: none; color: #e2e8f0; padding: 0; font-size: 0.85em; }
.md-render a { color: #22d3ee; text-decoration: underline; }
.md-render blockquote { border-left: 3px solid #475569; padding-left: 1em; margin: 0.8em 0; color: #94a3b8; }
.md-render table { border-collapse: collapse; margin: 0.8em 0; width: 100%; }
.md-render th, .md-render td { border: 1px solid #334155; padding: 0.5em 0.8em; text-align: left; color: #cbd5e1; }
.md-render th { background: #1e293b; font-weight: 600; }
.md-render tr:nth-child(even) { background: #0f172a; }
.md-render strong { color: #f1f5f9; font-weight: 600; }
.md-render em { color: #94a3b8; }
.md-render hr { border: none; border-top: 1px solid #334155; margin: 1.5em 0; }
.md-render img { max-width: 100%; border-radius: 4px; margin: 0.5em 0; }
`

export default function FileViewer({ filePath, onClose }) {
  const [content, setContent] = useState('')
  const [originalContent, setOriginalContent] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState('')
  const [highlightedHtml, setHighlightedHtml] = useState('')
  const [mdPreview, setMdPreview] = useState(true)
  const textareaRef = useRef(null)

  const fileName = filePath.split(/[\\/]/).pop() || filePath
  const lang = getLanguage(filePath)
  const isMd = isMarkdown(filePath)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    setEditing(false)
    setHighlightedHtml('')
    setSaveMsg('')

    async function load() {
      const res = await window.fileSystem.readFile(filePath)
      if (cancelled) return
      if (!res.ok) {
        setError(res.error)
        setLoading(false)
        return
      }
      setContent(res.content)
      setOriginalContent(res.content)
      setLoading(false)

      // Syntax highlight for non-markdown code files
      if (!isMd && lang) {
        const hl = await getHighlighter()
        if (hl && !cancelled) {
          try {
            const html = hl.codeToHtml(res.content, { lang, theme: 'github-dark' })
            setHighlightedHtml(html)
          } catch {
            // lang not loaded, show plain
          }
        }
      }
    }
    load()
    return () => { cancelled = true }
  }, [filePath])

  const handleSave = async () => {
    setSaving(true)
    setSaveMsg('')
    const res = await window.fileSystem.writeFile(filePath, content)
    setSaving(false)
    if (res.ok) {
      setOriginalContent(content)
      setSaveMsg('已保存')
      setTimeout(() => setSaveMsg(''), 2000)
      // Re-highlight if needed
      if (!isMd && lang) {
        const hl = await getHighlighter()
        if (hl) {
          try {
            const html = hl.codeToHtml(content, { lang, theme: 'github-dark' })
            setHighlightedHtml(html)
          } catch {}
        }
      }
    } else {
      setSaveMsg('保存失败: ' + (res.error || ''))
    }
  }

  const startEditing = () => {
    setEditing(true)
    if (isMd) setMdPreview(false)
  }

  const modified = content !== originalContent

  return (
    <div className="flex flex-col h-full bg-gray-900">
      <style>{mdStyles}</style>
      {/* Tab bar */}
      <div className="flex items-center gap-2 px-3 py-1.5 border-b border-gray-700/50 bg-gray-800/50 flex-shrink-0">
        <span className="text-[12px] text-gray-200 truncate flex-1" title={filePath}>
          {fileName}
          {modified && <span className="text-amber-400 ml-1">●</span>}
        </span>
        {saveMsg && (
          <span className={`text-[10px] ${saveMsg.startsWith('已') ? 'text-green-400' : 'text-red-400'}`}>{saveMsg}</span>
        )}
        {isMd && !editing && (
          <button
            onClick={() => setMdPreview(!mdPreview)}
            className="px-2 py-0.5 text-[10px] rounded bg-gray-700 text-gray-300 hover:bg-gray-600"
          >
            {mdPreview ? '源码' : '预览'}
          </button>
        )}
        {!editing ? (
          <button
            onClick={startEditing}
            className="px-2 py-0.5 text-[10px] rounded bg-gray-700 text-gray-300 hover:bg-gray-600"
          >
            编辑
          </button>
        ) : (
          <>
            <button
              onClick={handleSave}
              disabled={saving || !modified}
              className="px-2 py-0.5 text-[10px] rounded bg-cyan-600 text-white hover:bg-cyan-500 disabled:opacity-40"
            >
              {saving ? '...' : '保存'}
            </button>
            <button
              onClick={() => { setEditing(false); setContent(originalContent); if (isMd) setMdPreview(true) }}
              className="px-2 py-0.5 text-[10px] rounded bg-gray-700 text-gray-300 hover:bg-gray-600"
            >
              取消
            </button>
          </>
        )}
        <button
          onClick={onClose}
          className="p-0.5 rounded hover:bg-gray-700 text-gray-400 hover:text-gray-200"
          title="关闭"
        >
          <svg width="14" height="14" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M5 5l10 10M15 5L5 15" />
          </svg>
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {loading && (
          <div className="flex items-center justify-center h-full">
            <span className="text-[12px] text-gray-500">加载中...</span>
          </div>
        )}
        {error && (
          <div className="p-4">
            <p className="text-[12px] text-red-400">{error}</p>
          </div>
        )}

        {/* Markdown preview mode */}
        {!loading && !error && isMd && mdPreview && !editing && (
          <div className="md-render p-6 max-w-none text-[14px] leading-relaxed">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          </div>
        )}

        {/* Editing mode (markdown source or any file) */}
        {!loading && !error && editing && (
          <textarea
            ref={textareaRef}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className="w-full h-full p-4 bg-transparent text-[13px] text-gray-200 font-mono resize-none focus:outline-none leading-relaxed"
            spellCheck={false}
            autoFocus
          />
        )}

        {/* Markdown source view (non-editing) */}
        {!loading && !error && isMd && !mdPreview && !editing && (
          <pre className="p-4 text-[13px] text-gray-300 font-mono whitespace-pre-wrap leading-relaxed">{content}</pre>
        )}

        {/* Code file: syntax highlighted view */}
        {!loading && !error && !isMd && !editing && highlightedHtml && (
          <div
            className="p-4 text-[13px] overflow-x-auto [&_pre]:!bg-transparent [&_code]:!text-[13px] [&_pre]:!p-0"
            dangerouslySetInnerHTML={{ __html: highlightedHtml }}
          />
        )}

        {/* Code file: plain fallback */}
        {!loading && !error && !isMd && !editing && !highlightedHtml && (
          <pre className="p-4 text-[13px] text-gray-300 font-mono whitespace-pre-wrap">{content}</pre>
        )}
      </div>
    </div>
  )
}
