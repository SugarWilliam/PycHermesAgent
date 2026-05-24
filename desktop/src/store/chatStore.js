import { create } from 'zustand'
import { streamAgent, extractCitationsFromToolContent } from '../services/sidecarClient'
import useCitationStore from './citationStore'
import useSkillStore from './skillStore'
import useUiStore from './uiStore'

/** Map server `analysis_card` (snake_case) to ContextPanel `contextData` shape. */
function analysisCardToContextData(card) {
  if (!card || typeof card !== 'object') return null
  return {
    method: card.method,
    evidenceGrade: card.evidence_grade ?? card.evidenceGrade,
    srGrade: card.sr_grade ?? card.srGrade,
    rationale: card.rationale,
    citations: Array.isArray(card.citations) ? card.citations : [],
    risks: Array.isArray(card.risks) ? card.risks : [],
    assumptions: Array.isArray(card.assumptions) ? card.assumptions : [],
    degraded: Boolean(card.degraded),
    evidenceChain: card.evidence_chain ?? card.evidenceChain ?? null,
    networkRefs: Array.isArray(card.network_refs) ? card.network_refs : [],
    formalGroundingRefs: Array.isArray(card.formal_grounding_refs) ? card.formal_grounding_refs : [],
  }
}

const useChatStore = create((set, get) => ({
  conversations: [],
  activeConversationId: null,
  isStreaming: false,
  streamController: null,

  createConversation: () => {
    const id = crypto.randomUUID()
    const conv = { id, title: 'New Chat', messages: [], createdAt: Date.now() }
    set((s) => ({
      conversations: [conv, ...s.conversations],
      activeConversationId: id
    }))
    return id
  },

  setActiveConversation: (id) => set({ activeConversationId: id }),

  addMessage: (conversationId, message) => {
    set((s) => ({
      conversations: s.conversations.map((c) =>
        c.id === conversationId
          ? { ...c, messages: [...c.messages, { id: crypto.randomUUID(), ...message }] }
          : c
      )
    }))
  },

  appendDelta: (conversationId, delta) => {
    set((s) => ({
      conversations: s.conversations.map((c) => {
        if (c.id !== conversationId) return c
        const msgs = [...c.messages]
        const last = msgs[msgs.length - 1]
        if (last && last.role === 'assistant') {
          msgs[msgs.length - 1] = { ...last, content: last.content + delta }
        }
        return { ...c, messages: msgs }
      })
    }))
  },

  updateLastAssistantMeta: (conversationId, meta) => {
    set((s) => ({
      conversations: s.conversations.map((c) => {
        if (c.id !== conversationId) return c
        const msgs = [...c.messages]
        const last = msgs[msgs.length - 1]
        if (last && last.role === 'assistant') {
          msgs[msgs.length - 1] = { ...last, ...meta }
        }
        return { ...c, messages: msgs }
      })
    }))
  },

  setStreaming: (val) => set({ isStreaming: val }),

  stopStreaming: () => {
    const ctrl = get().streamController
    if (ctrl) ctrl.abort()
    set({ isStreaming: false, streamController: null })
  },

  /**
   * Send a user message and stream the assistant response.
   * @param {string} text - user message content
   * @param {string} analysisMode - 'casual' | 'structured' | 'formal'
   */
  sendMessage: (text, analysisMode = 'casual') => {
    const state = get()
    if (state.isStreaming) return

    let convId = state.activeConversationId
    if (!convId) {
      convId = get().createConversation()
    }

    useCitationStore.getState().clearCitations()
    useUiStore.getState().setFormalContextSnapshot(null)

    // Add user message
    get().addMessage(convId, { role: 'user', content: text, analysisMode })

    // Add empty assistant message placeholder
    get().addMessage(convId, {
      role: 'assistant',
      content: '',
      toolCalls: [],
      toolResults: [],
      traceId: null,
      model: null
    })

    set({ isStreaming: true })

    // Build request
    const messages = get()
      .conversations.find((c) => c.id === convId)
      ?.messages.filter((m) => m.role === 'user' || m.role === 'assistant')
      .map((m) => ({ role: m.role, content: m.content })) || []

    const activated_skills = useSkillStore.getState().getActiveSkillNames()

    const request = {
      messages,
      analysis_mode: analysisMode,
      planning_enabled: analysisMode !== 'casual',
      max_iterations: analysisMode === 'formal' ? 12 : 8,
      activated_skills
    }

    const controller = streamAgent(request, {
      onStart: (event) => {
        get().updateLastAssistantMeta(convId, {
          traceId: event.trace_id,
          model: event.model,
          sessionId: event.session_id
        })
      },
      onDelta: (event) => {
        if (event.delta) {
          get().appendDelta(convId, event.delta)
        }
      },
      onToolCall: (event) => {
        const calls = event.tool_calls || []
        get().updateLastAssistantMeta(convId, {
          toolCalls: calls.map((tc) => ({
            id: tc.id,
            name: tc.function?.name || tc.name,
            arguments: tc.function?.arguments || tc.arguments
          }))
        })
      },
      onToolResult: (event) => {
        const payload = event.payload && typeof event.payload === 'object' ? event.payload : {}
        const entry = {
          name: payload.tool_call?.name || payload.tool_call?.function?.name,
          tool_call_id: payload.tool_call?.id || payload.tool_result?.tool_call_id,
          content:
            typeof payload.tool_result?.content === 'string'
              ? payload.tool_result.content
              : payload.tool_result?.content != null
                ? JSON.stringify(payload.tool_result.content)
                : '',
          auto_injected: Boolean(payload.auto_injected)
        }
        set((s) => ({
          conversations: s.conversations.map((c) => {
            if (c.id !== convId) return c
            const msgs = [...c.messages]
            const last = msgs[msgs.length - 1]
            if (!last || last.role !== 'assistant') return c
            const prev = Array.isArray(last.toolResults) ? last.toolResults : []
            msgs[msgs.length - 1] = {
              ...last,
              toolResults: [...prev, entry]
            }
            return { ...c, messages: msgs }
          })
        }))
        const cites = extractCitationsFromToolContent(entry.content)
        if (cites.length > 0) {
          useCitationStore.getState().appendCitations(cites)
        }
      },
      onDone: (event) => {
        const meta = { finishReason: event.finish_reason || 'stop' }
        if (event.payload?.analysis_card || event.analysis_card) {
          const raw = event.payload?.analysis_card || event.analysis_card
          meta.analysisCard = raw
          useUiStore.getState().setFormalContextSnapshot(analysisCardToContextData(raw))
        }
        get().updateLastAssistantMeta(convId, meta)
        set({ isStreaming: false, streamController: null })
      },
      onError: (err) => {
        get().appendDelta(convId, `\n\n**Error:** ${err.message}`)
        set({ isStreaming: false, streamController: null })
      },
      onAbort: () => {
        get().updateLastAssistantMeta(convId, { finishReason: 'aborted' })
        set({ isStreaming: false, streamController: null })
      }
    })

    set({ streamController: controller })
  },

  deleteConversation: (id) => {
    set((s) => ({
      conversations: s.conversations.filter((c) => c.id !== id),
      activeConversationId: s.activeConversationId === id ? null : s.activeConversationId
    }))
  }
}))

export default useChatStore
