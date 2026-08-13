import { useState } from 'react'
import type { ChatMessage } from '../types'

interface Props {
  message: ChatMessage
}

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl bg-panel border border-border px-4 py-2.5 text-sm leading-relaxed text-fg">
          <p className="whitespace-pre-wrap">{message.text}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {message.thoughtSeconds != null && <Thought seconds={message.thoughtSeconds} />}
      {message.files.length > 0 && <EditedFiles files={message.files} />}
      {message.text && <p className="whitespace-pre-wrap text-sm leading-relaxed text-fg">{message.text}</p>}
      {message.pending && !message.text && (
        <span className="text-muted text-sm animate-pulse">Thinking…</span>
      )}
      {message.error && <p className="text-red-400 text-xs">⚠️ {message.error}</p>}
    </div>
  )
}

function Thought({ seconds }: { seconds: number }) {
  const [open, setOpen] = useState(false)
  return (
    <button
      onClick={() => setOpen(!open)}
      className="flex items-center gap-2 rounded-lg border border-border bg-deep/40 px-3 py-1.5 text-xs text-muted hover:text-fg"
    >
      <span className="text-muted">💭</span>
      <span>Thought for {seconds} second{seconds === 1 ? '' : 's'}</span>
      <span className="ml-1 text-muted">{open ? '▾' : '▸'}</span>
    </button>
  )
}

function EditedFiles({ files }: { files: { path: string; lang: string; summary: string }[] }) {
  const [open, setOpen] = useState(true)
  return (
    <div className="rounded-lg border border-border bg-deep/40">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-3 py-1.5 text-xs text-muted hover:text-fg"
      >
        <span>Edited files {files.length}</span>
        <span>{open ? '▾' : '▸'}</span>
      </button>
      {open && (
        <div className="border-t border-border">
          {files.map((f, i) => (
            <div key={i} className="flex items-center gap-2 px-3 py-1.5 text-xs font-mono text-fg/90">
              <span className="text-muted">▸</span>
              <span className="truncate">{f.path}</span>
              <span className="ml-auto rounded bg-panel px-1.5 py-0.5 text-[10px] text-muted">{f.lang}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
