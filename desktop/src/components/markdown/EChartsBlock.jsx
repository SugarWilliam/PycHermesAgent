import { useEffect, useRef, useState } from 'react'
import * as echarts from 'echarts'

export default function EChartsBlock({ value, height = 400 }) {
  const containerRef = useRef(null)
  const chartRef = useRef(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!value || !containerRef.current) return

    let option
    try {
      option = JSON.parse(value)
    } catch (err) {
      setError(`JSON parse error: ${err.message}`)
      return
    }

    // Allow option to specify height
    const h = option._height || height
    containerRef.current.style.height = `${h}px`

    try {
      const chart = echarts.init(containerRef.current, 'dark')
      chartRef.current = chart
      chart.setOption(option)
    } catch (err) {
      setError(`ECharts error: ${err.message}`)
      return
    }

    const ro = new ResizeObserver(() => {
      chartRef.current?.resize()
    })
    ro.observe(containerRef.current)

    return () => {
      ro.disconnect()
      chartRef.current?.dispose()
      chartRef.current = null
    }
  }, [value, height])

  if (error) {
    return (
      <div className="my-3 rounded-lg border border-red-300 dark:border-red-700 overflow-hidden">
        <div className="px-3 py-1.5 bg-red-50 dark:bg-red-900/30 text-xs text-red-600 dark:text-red-400">
          {error}
        </div>
        <pre className="p-4 overflow-x-auto bg-gray-50 dark:bg-gray-900 text-sm font-mono">{value}</pre>
      </div>
    )
  }

  return (
    <div className="my-3 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
      <div ref={containerRef} style={{ width: '100%', height: `${height}px` }} />
    </div>
  )
}
