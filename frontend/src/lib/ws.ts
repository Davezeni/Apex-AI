// WebSocket client that dispatches backend agent events into the chat store.
import { useChat } from '../stores/useChat'
import type { AgentEvent, ToolStep } from '../types'

let socket: WebSocket | null = null
let turnStart = 0
let conversationId: string | null = null

export function setConversationId(id: string | null) {
  conversationId = id
}

export function getConversationId() {
  return conversationId
}

export function sendMessage(message: string) {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    connect()
    socket!.addEventListener('open', () => socket!.send(JSON.stringify({ message, conversation_id: conversationId })), { once: true })
    return
  }
  socket.send(JSON.stringify({ message, conversation_id: conversationId }))
}

export function connect() {
  if (socket && socket.readyState !== WebSocket.CLOSED) return

  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  socket = new WebSocket(`${proto}://${location.host}/ws/chat`)
  const store = useChat.getState()

  socket.addEventListener('message', (ev) => {
    const event = JSON.parse(ev.data) as AgentEvent
    switch (event.type) {
      case 'TextDelta':
        store.appendDelta(event.delta)
        break
      case 'Thinking':
        store.setThinking(event.text)
        break
      case 'ToolCallEvent':
        store.appendStep({ name: event.name, ok: true, summary: 'running…', durationSeconds: 0, detail: {} })
        if (event.name === 'write_file' || event.name === 'edit_file' || event.name === 'create_structure') {
          const path = (event.arguments as { path?: string })?.path || ''
          if (path) store.markFile({ path, lang: '', summary: event.name.replace('_', ' ') })
        }
        break
      case 'ToolResultEvent':
        replaceLastStep({
          name: event.name,
          ok: event.ok,
          summary: event.summary,
          durationSeconds: event.durationSeconds,
          detail: event.detail,
        })
        break
      case 'Review':
        setReview(event.text)
        break
      case 'Done':
        if (turnStart) store.setThought(Math.max(1, Math.round((Date.now() - turnStart) / 1000)))
        store.finishMessage()
        break
      case 'Error':
        store.failMessage(event.message)
        break
    }
  })

  socket.addEventListener('close', () => {
    store.setStreaming(false)
    socket = null
  })

  socket.addEventListener('error', () => {
    // Surface connection failure instead of leaving a message stuck "pending".
    store.failMessage('connection lost — please retry')
    store.setStreaming(false)
    socket = null
  })

  turnStart = Date.now()
}

function replaceLastStep(step: ToolStep) {
  useChat.setState((s) => {
    const msgs = [...s.messages]
    const last = msgs[msgs.length - 1]
    if (!last || last.role !== 'assistant') return { messages: msgs }
    const steps = [...last.steps]
    if (steps.length > 0) steps[steps.length - 1] = step
    msgs[msgs.length - 1] = { ...last, steps }
    return { messages: msgs }
  })
}

function setReview(text: string) {
  useChat.setState((s) => {
    const msgs = [...s.messages]
    const last = msgs[msgs.length - 1]
    if (!last || last.role !== 'assistant') return { messages: msgs }
    msgs[msgs.length - 1] = { ...last, review: text }
    return { messages: msgs }
  })
}
