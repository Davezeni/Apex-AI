import type { ChatMessage } from '../types'

interface Props {
  message: ChatMessage
}

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser ? 'bg-accent text-white' : 'bg-panel border border-border'
        }`}
      >
        {message.steps.length > 0 && <Steps steps={message.steps} />}
        {message.text && <p className="whitespace-pre-wrap">{message.text}</p>}
        {message.pending && !message.text && (
          <span className="text-neutral-400 animate-pulse">Thinking…</span>
        )}
        {message.error && (
          <p className="text-red-400 text-xs mt-1">⚠️ {message.error}</p>
        )}
      </div>
    </div>
  )
}

function Steps({ steps }: { steps: { name: string; ok: boolean; summary: string }[] }) {
  return (
    <div className="mb-2 space-y-1.5">
      {steps.map((s, i) => (
        <div key={i} className="text-xs rounded-lg bg-surface px-2.5 py-1.5 border border-border">
          <span className="font-mono text-neutral-400">🔧 {s.name}</span>{' '}
          <span className={s.ok ? 'text-neutral-300' : 'text-red-400'}>{s.summary}</span>
        </div>
      ))}
    </div>
  )
}
