import { useRef, useState } from 'react'
import { sendMessage } from '../lib/ws'
import { useChat } from '../stores/useChat'
import MessageBubble from './MessageBubble'

const MAX_LINES = 6

export default function Chat() {
  const messages = useChat((s) => s.messages)
  const streaming = useChat((s) => s.streaming)
  const addMessage = useChat((s) => s.addMessage)
  const setStreaming = useChat((s) => s.setStreaming)

  const [input, setInput] = useState('')
  const [uploading, setUploading] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const taRef = useRef<HTMLTextAreaElement>(null)

  // Auto-grow the textarea up to MAX_LINES.
  const autoGrow = () => {
    const ta = taRef.current
    if (!ta) return
    ta.style.height = 'auto'
    const lineHeight = 22
    const maxHeight = lineHeight * MAX_LINES
    ta.style.height = `${Math.min(ta.scrollHeight, maxHeight)}px`
    ta.style.overflowY = ta.scrollHeight > maxHeight ? 'auto' : 'hidden'
  }

  const submit = () => {
    const text = input.trim()
    if (!text || streaming) return
    addMessage({ id: `u${Date.now()}`, role: 'user', text, steps: [], files: [], thoughtSeconds: null, thinking: '' })
    setStreaming(true)
    setInput('')
    requestAnimationFrame(() => {
      const ta = taRef.current
      if (ta) ta.style.height = 'auto'
    })
    sendMessage(text)
    requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight })
    })
  }

  const upload = async (file: File) => {
    setUploading(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const r = await fetch('/api/workspace/upload', { method: 'POST', body: fd })
      if (!r.ok) throw new Error(await r.text())
      addMessage({
        id: `u${Date.now()}`,
        role: 'user',
        text: `📎 Uploaded ${file.name}`,
        steps: [],
        files: [],
        thoughtSeconds: null, thinking: '',
      })
      // Ask the agent to read it so it becomes aware of the file's content.
      sendMessage(`I just uploaded the file "${file.name}". Please read it (use parse_document, describe_image, or ocr_image as appropriate) and summarize what it contains.`)
    } catch {
      addMessage({
        id: `u${Date.now()}`,
        role: 'user',
        text: `⚠️ Upload failed: ${file.name}`,
        steps: [],
        files: [],
        thoughtSeconds: null, thinking: '',
      })
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col bg-surface">
      <div ref={scrollRef} className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4">
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

      {/* Input bar: everything inside one rounded container */}
      <form onSubmit={(e) => { e.preventDefault(); submit() }} className="border-t border-border p-2">
        <div className="flex items-end gap-2 rounded-2xl border border-border bg-panel px-2 py-1.5 focus-within:border-muted">
          <input
            ref={fileRef}
            type="file"
            multiple
            accept="image/*,.pdf,.csv,.xlsx,.docx,.txt,.md,.json,.zip"
            className="hidden"
            onChange={(e) => {
              const files = e.target.files
              if (files) Array.from(files).forEach((f) => upload(f))
              e.target.value = ''
            }}
          />
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            title="Attach file"
            aria-label="Attach file"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-muted transition-colors hover:bg-surface hover:text-fg disabled:opacity-40"
          >
            {uploading ? (
              <span className="text-xs">…</span>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
              </svg>
            )}
          </button>

          <textarea
            ref={taRef}
            value={input}
            onChange={(e) => { setInput(e.target.value); autoGrow() }}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() } }}
            rows={1}
            placeholder="Ask Apex AI…"
            className="min-h-9 max-h-[140px] flex-1 resize-none bg-transparent py-2 text-sm text-fg placeholder:text-muted focus:outline-none"
          />

          <button
            type="submit"
            disabled={streaming || !input.trim()}
            title="Send"
            aria-label="Send message"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-accent text-white transition-colors disabled:opacity-40 hover:bg-accent/90"
          >
            {/* Telegram-style send arrow */}
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" transform="translate(-1 1) rotate(0)">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" fill="currentColor" stroke="none" />
            </svg>
          </button>
        </div>
      </form>
    </div>
  )
}
