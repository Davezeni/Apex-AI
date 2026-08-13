import { useRef, useState } from 'react'
import { sendMessage } from '../lib/ws'
import { useChat } from '../stores/useChat'
import MessageBubble from './MessageBubble'

export default function Chat() {
  const messages = useChat((s) => s.messages)
  const streaming = useChat((s) => s.streaming)
  const addMessage = useChat((s) => s.addMessage)
  const setStreaming = useChat((s) => s.setStreaming)

  const [input, setInput] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)

  const submit = () => {
    const text = input.trim()
    if (!text || streaming) return
    addMessage({ id: `u${Date.now()}`, role: 'user', text, steps: [], files: [], thoughtSeconds: null })
    setStreaming(true)
    setInput('')
    sendMessage(text)
    requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight })
    })
  }

  return (
    <div className="flex h-full flex-col bg-surface">
      <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto p-4">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center text-center text-muted">
            <div className="mb-2 text-3xl">🛠️</div>
            <p className="max-w-xs text-sm">
              Ask Apex AI to build something. It can create files, scaffold projects, and search the web.
            </p>
          </div>
        )}
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
      </div>

      <form onSubmit={(e) => { e.preventDefault(); submit() }} className="border-t border-border p-3">
        <div className="flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() } }}
            rows={1}
            placeholder="Ask Apex AI…"
            className="flex-1 resize-none rounded-xl bg-panel border border-border px-3 py-2.5 text-sm text-fg placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-muted"
          />
          <button
            type="submit"
            disabled={streaming || !input.trim()}
            className="rounded-xl bg-panel border border-border px-4 py-2.5 text-sm font-medium text-fg disabled:opacity-40 hover:border-muted"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  )
}
