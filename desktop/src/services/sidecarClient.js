/**
 * Sidecar HTTP + SSE client.
 *
 * Connects to the Python sidecar at a main-process-authoritative base URL and provides
 * methods for health checks, non-streaming calls, and SSE streaming.
 */

const DEFAULT_BASE_URL = 'http://127.0.0.1:8765'

async function getBaseUrl() {
  if (!window.sidecar?.getRuntimeConfig) return DEFAULT_BASE_URL
  const runtime = await window.sidecar.getRuntimeConfig()
  return runtime.resolved_url || DEFAULT_BASE_URL
}

/**
 * Check sidecar health.
 * @returns {Promise<object>} health payload
 */
export async function checkHealth() {
  if (window.sidecar?.checkHealth) {
    return window.sidecar.checkHealth()
  }

  const res = await fetch(`${await getBaseUrl()}/health`)
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`)
  return res.json()
}

/**
 * Non-streaming agent run.
 * @param {object} request - AgentLoopRequest fields
 * @returns {Promise<object>} result payload
 */
export async function runAgent(request) {
  const res = await fetch(`${await getBaseUrl()}/agent/run`, {
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
 * @param {object} handlers - { onStart, onDelta, onToolCall, onToolResult, onDone, onError, onAbort }
 * @returns {AbortController} - call .abort() to cancel the stream
 */
export function streamAgent(request, handlers = {}) {
  const controller = new AbortController()

  ;(async () => {
    let sawDone = false
    try {
      const baseUrl = await getBaseUrl()
      const res = await fetch(`${baseUrl}/agent/run/stream`, {
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
            case 'plan':
            case 'assistant.completed':
            case 'retry':
              handlers.onEvent?.(event)
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
      if (err.name === 'AbortError') {
        handlers.onAbort?.()
      } else {
        handlers.onError?.(err)
      }
    }
  })()

  return controller
}

/**
 * Fetch all skills.
 * @returns {Promise<object[]>} skills list
 */
export async function fetchSkills() {
  const res = await fetch(`${await getBaseUrl()}/skills`)
  if (!res.ok) throw new Error(`Fetch skills failed: ${res.status}`)
  return res.json()
}

/**
 * List AGENTS.md / CLAUDE.md rule sources ordered by precedence (matches sidecar `/rules`).
 * @returns {Promise<object>} `{ items: ... }`
 */
export async function fetchRules() {
  const res = await fetch(`${await getBaseUrl()}/rules`)
  if (!res.ok) throw new Error(`Fetch rules failed: ${res.status}`)
  return res.json()
}

/**
 * Rules fingerprint bundle (`path`, bytes, SHA-256 digest) aligned with precedence order — for audit/export.
 * @returns {Promise<object>}
 */
export async function fetchRulesManifest() {
  const res = await fetch(`${await getBaseUrl()}/rules/manifest`)
  if (!res.ok) throw new Error(`Fetch rules manifest failed: ${res.status}`)
  return res.json()
}

/**
 * Persist Markdown for a workspace-scoped user skill (writable runtime `user_skills/`).
 * @param {string} skillId - Skill id / slug (`skill_id`)
 * @param {string} markdown - Full SKILL.md body (YAML frontmatter supported)
 */
export async function saveUserSkill(skillId, markdown) {
  const res = await fetch(`${await getBaseUrl()}/skills/user`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ skill_id: skillId, markdown })
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }))
    throw new Error(err.error?.message || err.message || `Save user skill failed: ${res.status}`)
  }
  return res.json()
}

/**
 * Load sidecar-backed user preferences (Hermes memory / analysis defaults).
 * @returns {Promise<object>}
 */
export async function fetchPreferences() {
  const res = await fetch(`${await getBaseUrl()}/preferences`)
  if (!res.ok) throw new Error(`Fetch preferences failed: ${res.status}`)
  return res.json()
}

/**
 * List indexed knowledge bases (MRAG Phase 3).
 * @returns {Promise<object>} `{ items: [...] }` — each item may include `knowledge_base_id`, `display_name`
 */
export async function listKnowledgeBases() {
  const res = await fetch(`${await getBaseUrl()}/knowledge-bases`)
  if (!res.ok) throw new Error(`List knowledge bases failed: ${res.status}`)
  return res.json()
}

/**
 * Search within a knowledge base.
 * @param {string} knowledgeBaseId - MRAG knowledge_base_id
 * @param {object} body - RetrievalRequest-compatible fields ({ query, top_k?, retrieval_mode?, semantic_weight?, include_citations? })
 * @returns {Promise<object>} serialized RetrievalResult
 */
export async function searchKnowledgeBase(knowledgeBaseId, body) {
  const encoded = encodeURIComponent(knowledgeBaseId)
  const res = await fetch(`${await getBaseUrl()}/knowledge-bases/${encoded}/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }))
    throw new Error(err.error?.message || err.message || `KB search failed: ${res.status}`)
  }
  return res.json()
}

/**
 * Try to collect MRAG-style citation objects from a tool result JSON body.
 * @param {unknown} content - tool_result.content (often a stringified JSON)
 * @returns {object[]}
 */
export function extractCitationsFromToolContent(content) {
  if (typeof content !== 'string' || !content.trim()) return []
  let data
  try {
    data = JSON.parse(content)
  } catch {
    return []
  }
  if (!data || typeof data !== 'object') return []
  const fromRoot = data.citations
  const fromRetrieval = data.retrieval && data.retrieval.citations
  const fromNested = data.result && data.result.citations
  const raw = Array.isArray(fromRoot) ? fromRoot : Array.isArray(fromRetrieval) ? fromRetrieval : Array.isArray(fromNested) ? fromNested : []
  return raw.filter((c) => c && typeof c === 'object')
}

/**
 * Activate a skill.
 * @param {string} id - skill ID
 */
export async function activateSkill(id) {
  const res = await fetch(`${await getBaseUrl()}/skills/${id}/activate`, { method: 'POST' })
  if (!res.ok) throw new Error(`Activate skill failed: ${res.status}`)
  return res.json()
}

/**
 * Deactivate a skill.
 * @param {string} id - skill ID
 */
export async function deactivateSkill(id) {
  const res = await fetch(`${await getBaseUrl()}/skills/${id}/deactivate`, { method: 'POST' })
  if (!res.ok) throw new Error(`Deactivate skill failed: ${res.status}`)
  return res.json()
}

export async function runFormalAnalysis(request) {
  const res = await fetch(`${await getBaseUrl()}/formal-analysis`, {
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

/**
 * List sidecar artifact records (`ArtifactEngine`).
 * @param {string} [taskId] - Optional task scope (`GET /artifacts/task/{task_id}`)
 * @returns {Promise<object>} `{ items, task_id? }`
 */
export async function fetchArtifacts(taskId) {
  const base = await getBaseUrl()
  const path =
    taskId != null && String(taskId).trim()
      ? `/artifacts/task/${encodeURIComponent(String(taskId).trim())}`
      : '/artifacts'
  const res = await fetch(`${base}${path}`)
  if (!res.ok) throw new Error(`Fetch artifacts failed: ${res.status}`)
  return res.json()
}

/**
 * Create structured XLSX/PPTX artifacts on the sidecar (Phase 3 Track E).
 * @param {object} payload - `{ task_id, format: 'xlsx'|'pptx', spec, filename? }`
 * @returns {Promise<object>}
 */
export async function exportOfficeArtifact(payload) {
  const res = await fetch(`${await getBaseUrl()}/artifacts/office`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }))
    throw new Error(err.error?.message || err.message || `Office export failed: ${res.status}`)
  }
  return res.json()
}
