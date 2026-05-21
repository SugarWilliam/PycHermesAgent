import { create } from 'zustand'
import { streamAgent } from '../services/sidecarClient'

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

    // Add user message
    get().addMessage(convId, { role: 'user', content: text, analysisMode })

    // Add empty assistant message placeholder
    get().addMessage(convId, {
      role: 'assistant',
      content: '',
      toolCalls: [],
      traceId: null,
      model: null
    })

    set({ isStreaming: true })

    // Build request
    const messages = get()
      .conversations.find((c) => c.id === convId)
      ?.messages.filter((m) => m.role === 'user' || m.role === 'assistant')
      .map((m) => ({ role: m.role, content: m.content })) || []

    const request = {
      messages,
      analysis_mode: analysisMode,
      planning_enabled: analysisMode !== 'casual',
      max_iterations: analysisMode === 'formal' ? 12 : 8
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
      onDone: (event) => {
        const meta = { finishReason: event.finish_reason || 'stop' }
        if (event.payload?.analysis_card || event.analysis_card) {
          meta.analysisCard = event.payload?.analysis_card || event.analysis_card
        }
        get().updateLastAssistantMeta(convId, meta)
        set({ isStreaming: false, streamController: null })
      },
      onError: (err) => {
        get().appendDelta(convId, `\n\n**Error:** ${err.message}`)
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
