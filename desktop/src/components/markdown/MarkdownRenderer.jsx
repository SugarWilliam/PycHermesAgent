import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import CodeBlock from './CodeBlock'
import MermaidBlock from './MermaidBlock'
import EChartsBlock from './EChartsBlock'
import CalloutBlock from './CalloutBlock'
import katex from 'katex'

const remarkPlugins = [remarkGfm, remarkMath]
const rehypePlugins = [rehypeKatex]

function KaTeXBlock({ value }) {
  try {
    const html = katex.renderToString(value, { displayMode: true, throwOnError: false })
    return <div className="my-3 overflow-x-auto" dangerouslySetInnerHTML={{ __html: html }} />
  } catch {
    return <pre className="p-4 my-3 bg-gray-50 dark:bg-gray-900 text-sm font-mono">{value}</pre>
  }
}

const components = {
  code({ node, inline, className, children, ...props }) {
    const match = /language-(\w+)/.exec(className || '')
    const lang = match ? match[1] : null
    const value = String(children).replace(/\n$/, '')

    if (inline || !match) {
      return (
        <code
          className="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-sm font-mono"
          {...props}
        >
          {children}
        </code>
      )
    }

    if (lang === 'mermaid') return <MermaidBlock value={value} />
    if (lang === 'echarts') return <EChartsBlock value={value} />
    if (lang === 'math' || lang === 'latex') return <KaTeXBlock value={value} />

    return <CodeBlock language={lang} value={value} />
  },
  blockquote({ children }) {
    return <CalloutBlock>{children}</CalloutBlock>
  },
  table({ children }) {
    return (
      <div className="overflow-x-auto my-3">
        <table className="min-w-full text-sm border border-gray-200 dark:border-gray-700">
          {children}
        </table>
      </div>
    )
  },
  th({ children }) {
    return (
      <th className="px-3 py-2 text-left bg-gray-100 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 font-medium">
        {children}
      </th>
    )
  },
  td({ children }) {
    return (
      <td className="px-3 py-2 border-b border-gray-100 dark:border-gray-800">{children}</td>
    )
  }
}

export default function MarkdownRenderer({ content }) {
  if (!content) return null
  return (
    <ReactMarkdown
      remarkPlugins={remarkPlugins}
      rehypePlugins={rehypePlugins}
      components={components}
    >
      {content}
    </ReactMarkdown>
  )
}
