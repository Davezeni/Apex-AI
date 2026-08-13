// WebSocket client that dispatches backend agent events into the chat store.
import { useChat } from '../stores/useChat'
import type { AgentEvent } from '../types'

let socket: WebSocket | null = null

export function sendMessage(message: string) {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    connect()
    // wait for open before sending
    socket!.addEventListener('open', () => socket!.send(JSON.stringify({ message })), {
      once: true,
    })
    return
  }
  socket.send(JSON.stringify({ message }))
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
      case 'ToolCallEvent':
        store.appendStep({ name: event.name, ok: true, summary: 'running…' })
        break
      case 'ToolResultEvent':
        // replace the placeholder step summary (best-effort: mark last step)
        replaceLastStep({ name: event.name, ok: event.ok, summary: event.summary })
        break
      case 'Done':
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
}

function replaceLastStep(step: { name: string; ok: boolean; summary: string }) {
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
