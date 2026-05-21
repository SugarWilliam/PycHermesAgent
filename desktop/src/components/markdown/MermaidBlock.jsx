import { useEffect, useRef, useState } from 'react'
import mermaid from 'mermaid'

let mermaidId = 0

mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  securityLevel: 'loose'
})

export default function MermaidBlock({ value }) {
  const containerRef = useRef(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!value || !containerRef.current) return
    let cancelled = false
    const id = `mermaid-${++mermaidId}`

    ;(async () => {
      try {
        const { svg } = await mermaid.render(id, value)
        if (!cancelled && containerRef.current) {
          containerRef.current.innerHTML = svg
        }
      } catch (err) {
        if (!cancelled) setError(err.message || 'Mermaid render failed')
      }
    })()

    return () => { cancelled = true }
  }, [value])

  if (error) {
    return (
      <div className="my-3 rounded-lg border border-red-300 dark:border-red-700 overflow-hidden">
        <div className="px-3 py-1.5 bg-red-50 dark:bg-red-900/30 text-xs text-red-600 dark:text-red-400">
          Mermaid Error: {error}
        </div>
        <pre className="p-4 overflow-x-auto bg-gray-50 dark:bg-gray-900 text-sm font-mono">{value}</pre>
      </div>
    )
  }

  return (
    <div className="my-3 flex justify-center overflow-x-auto">
      <div ref={containerRef} />
    </div>
  )
}
