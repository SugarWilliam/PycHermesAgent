/**
 * Sidecar HTTP + SSE client.
 *
 * Connects to the Python sidecar at a configurable base URL and provides
 * methods for health checks, non-streaming calls, and SSE streaming.
 */

import useSettingsStore from '../store/settingsStore'

const DEFAULT_BASE_URL = 'http://127.0.0.1:8765'

function getBaseUrl() {
  const stored = useSettingsStore.getState().sidecarUrl
  return window.__SIDECAR_URL__ || stored || DEFAULT_BASE_URL
}

/**
 * Check sidecar health.
 * @returns {Promise<object>} health payload
 */
export async function checkHealth() {
  const res = await fetch(`${getBaseUrl()}/health`)
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`)
  return res.json()
}

/**
 * Non-streaming agent run.
 * @param {object} request - AgentLoopRequest fields
 * @returns {Promise<object>} result payload
 */
export async function runAgent(request) {
  const res = await fetch(`${getBaseUrl()}/agent/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }))
    throw new Error(err.message || err.error || `Agent run failed: ${res.status}`)
  }
  return res.json()
}

/**
 * Stream agent loop events via SSE.
 *
 * @param {object} request - AgentLoopRequest fields
 * @param {object} handlers - { onStart, onDelta, onToolCall, onDone, onError }
 * @returns {AbortController} - call .abort() to cancel the stream
 */
export function streamAgent(request, handlers = {}) {
  const controller = new AbortController()

  ;(async () => {
    let sawDone = false
    try {
      const res = await fetch(`${getBaseUrl()}/agent/run/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
        signal: controller.signal
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: res.statusText }))
        handlers.onError?.(new Error(err.error?.message || err.message || `Stream failed: ${res.status}`), err)
        return
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const json = line.slice(6)
          if (!json.trim()) continue

          let event
          try {
            event = JSON.parse(json)
          } catch {
            continue
          }

          switch (event.event) {
            case 'start':
              handlers.onStart?.(event)
              break
            case 'assistant.delta':
              handlers.onDelta?.(event)
              break
            case 'assistant.tool_call.delta':
              handlers.onToolCall?.(event)
              break
            case 'tool.result':
              handlers.onToolResult?.(event)
              break
            case 'done':
              sawDone = true
              handlers.onDone?.(event)
              break
            case 'error':
              handlers.onError?.(new Error(event.error?.message || 'Stream error'), event)
              break
            default:
              handlers.onEvent?.(event)
          }
        }
      }

      if (!sawDone) {
        handlers.onDone?.({ event: 'done', finish_reason: 'stream_closed' })
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        handlers.onError?.(err)
      }
    }
  })()

  return controller
}

/**
 * Send a formal analysis request.
 * @param {object} request - MetaAnalysisRequest fields
 * @returns {Promise<object>} MetaAnalysisResult
 */
/**
 * Fetch all skills.
 * @returns {Promise<object[]>} skills list
 */
export async function fetchSkills() {
  const res = await fetch(`${getBaseUrl()}/skills`)
  if (!res.ok) throw new Error(`Fetch skills failed: ${res.status}`)
  return res.json()
}

/**
 * Activate a skill.
 * @param {string} id - skill ID
 */
export async function activateSkill(id) {
  const res = await fetch(`${getBaseUrl()}/skills/${id}/activate`, { method: 'POST' })
  if (!res.ok) throw new Error(`Activate skill failed: ${res.status}`)
  return res.json()
}

/**
 * Deactivate a skill.
 * @param {string} id - skill ID
 */
export async function deactivateSkill(id) {
  const res = await fetch(`${getBaseUrl()}/skills/${id}/deactivate`, { method: 'POST' })
  if (!res.ok) throw new Error(`Deactivate skill failed: ${res.status}`)
  return res.json()
}

export async function runFormalAnalysis(request) {
  const res = await fetch(`${getBaseUrl()}/formal-analysis`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }))
    throw new Error(err.error?.message || err.message || `Analysis failed: ${res.status}`)
  }
  return res.json()
}
