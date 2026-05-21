import { useState, useEffect } from 'react'
import { createHighlighter } from 'shiki'

let highlighterPromise = null

function getHighlighter() {
  if (!highlighterPromise) {
    highlighterPromise = createHighlighter({
      themes: ['github-dark'],
      langs: ['javascript', 'typescript', 'python', 'json', 'html', 'css', 'bash', 'markdown', 'yaml', 'rust', 'go', 'c', 'cpp', 'java', 'sql']
    }).catch(() => null)
  }
  return highlighterPromise
}

export default function CodeBlock({ language, value }) {
  const [copied, setCopied] = useState(false)
  const [html, setHtml] = useState('')

  useEffect(() => {
    let cancelled = false
    getHighlighter().then((hl) => {
      if (cancelled || !hl) return
      try {
        const langs = hl.getLoadedLanguages()
        const lang = langs.includes(language) ? language : 'text'
        const result = hl.codeToHtml(value, { lang, theme: 'github-dark' })
        if (!cancelled) setHtml(result)
      } catch {
        // fallback: leave html empty
      }
    })
    return () => { cancelled = true }
  }, [language, value])

  const handleCopy = () => {
    navigator.clipboard.writeText(value)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="relative my-3 rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700">
      <div className="flex items-center justify-between px-3 py-1.5 bg-gray-100 dark:bg-gray-800 text-xs text-gray-500 dark:text-gray-400">
        <span>{language}</span>
        <button
          onClick={handleCopy}
          className="hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
        >
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      {html ? (
        <div
          className="p-4 overflow-x-auto text-sm leading-relaxed [&_pre]:!bg-transparent [&_pre]:!m-0 [&_pre]:!p-0 bg-gray-900"
          dangerouslySetInnerHTML={{ __html: html }}
        />
      ) : (
        <pre className="p-4 overflow-x-auto bg-gray-50 dark:bg-gray-900 text-sm leading-relaxed">
          <code className="font-mono">{value}</code>
        </pre>
      )}
    </div>
  )
}
