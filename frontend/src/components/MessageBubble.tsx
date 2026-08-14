import { useEffect, useState } from 'react'
import type { ChatMessage, ToolStep } from '../types'

const COLLAPSE_LINES = 15

interface Props {
  message: ChatMessage
}

function CopyButton({ text, small = false }: { text: string; small?: boolean }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      onClick={() => {
        navigator.clipboard?.writeText(text).then(() => {
          setCopied(true)
          setTimeout(() => setCopied(false), 1200)
        })
      }}
      title="Copy"
      aria-label="Copy"
      className={`rounded border border-border text-muted transition-colors hover:text-fg ${small ? 'px-1.5 py-0.5 text-[10px]' : 'p-1'}`}
    >
      {copied ? '✓' : (
        <svg width={small ? 11 : 14} height={small ? 11 : 14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
        </svg>
      )}
    </button>
  )
}

export default function MessageBubble({ message }: Props) {
  if (message.role === 'user') {
    return (
      <div className="group flex justify-end">
        <div className="flex max-w-[85%] min-w-0 items-start gap-2">
          <div className="min-w-0 break-words rounded-2xl bg-panel border border-border px-4 py-2.5 text-sm leading-relaxed text-fg">
            <RichText text={message.text} />
          </div>
          <CopyButton text={message.text} />
        </div>
      </div>
    )
  }

  const done = !message.pending

  return (
    <div className="min-w-0 space-y-2">
      {(message.thoughtSeconds != null || message.thinking) && (
        <Thought seconds={message.thoughtSeconds} thinking={message.thinking} done={done} />
      )}
      {message.files.length > 0 && <EditedFiles files={message.files} />}
      {message.steps.length > 0 && <Steps steps={message.steps} />}
      {message.text && <RichText text={message.text} />}
      {message.review && <Collapsible label="🔍 Review" text={message.review} />}
      {message.summary && <Collapsible label="📋 Summary" text={message.summary} />}
      {message.pending && !message.text && <span className="text-muted text-sm animate-pulse">Thinking…</span>}
      {message.error && <p className="text-red-400 text-xs">⚠️ {message.error}</p>}
    </div>
  )
}

/** Collapsible prose block (review/summary): shows up to N lines, click to expand. */
function Collapsible({ label, text }: { label: string; text: string }) {
  const lines = text.split('\n')
  const [open, setOpen] = useState(lines.length <= COLLAPSE_LINES)

  const truncated = lines.slice(0, COLLAPSE_LINES).join('\n')
  const needsToggle = lines.length > COLLAPSE_LINES

  return (
    <div className="rounded-lg border border-border bg-deep/40">
      <div className="flex items-center gap-2 px-3 py-1.5 text-xs text-muted">
        <span>{label}</span>
        {needsToggle && (
          <button
            onClick={() => setOpen(!open)}
            className="ml-auto rounded border border-border px-1.5 py-0.5 text-[10px] text-muted hover:text-fg"
          >
            {open ? 'Show less' : `Show all (${lines.length} lines)`}
          </button>
        )}
      </div>
      <div className="border-t border-border px-3 py-2 text-xs leading-relaxed text-fg/90 whitespace-pre-wrap">
        {open ? text : truncated + '\n…'}
      </div>
    </div>
  )
}

/**
 * Lightweight markdown renderer for message text: splits on ``` fences and
 * renders each code block as a collapsible, max-N-lines code panel.
 */
function RichText({ text }: { text: string }) {
  const parts = splitFences(text)
  return (
    <div className="min-w-0 space-y-2 text-sm leading-relaxed text-fg">
      {parts.map((part, i) =>
        part.type === 'code' ? (
          <CodeBlock key={i} lang={part.lang || ''} code={part.code || ''} />
        ) : (
          <p key={i} className="whitespace-pre-wrap break-words">{part.text || ''}</p>
        ),
      )}
    </div>
  )
}

function splitFences(text: string): { type: 'text' | 'code'; text?: string; code?: string; lang?: string }[] {
  const parts: { type: 'text' | 'code'; text?: string; code?: string; lang?: string }[] = []
  const regex = /```([^\n]*)\n([\s\S]*?)```/g
  let last = 0
  let m: RegExpExecArray | null
  while ((m = regex.exec(text)) !== null) {
    if (m.index > last) {
      const before = text.slice(last, m.index)
      if (before.trim()) parts.push({ type: 'text', text: before })
    }
    parts.push({ type: 'code', lang: (m[1] || '').trim(), code: m[2] })
    last = m.index + m[0].length
  }
  if (last < text.length) {
    const after = text.slice(last)
    if (after.trim()) parts.push({ type: 'text', text: after })
  }
  if (parts.length === 0 && text.trim()) parts.push({ type: 'text', text })
  return parts
}

function CodeBlock({ lang, code }: { lang: string; code: string }) {
  const lines = code.split('\n')
  const [open, setOpen] = useState(lines.length <= COLLAPSE_LINES)
  const needsToggle = lines.length > COLLAPSE_LINES
  const shown = open ? code : lines.slice(0, COLLAPSE_LINES).join('\n') + '\n…'

  return (
    <div className="rounded-lg border border-border bg-ink/40 overflow-hidden">
      <div className="flex items-center gap-2 border-b border-border bg-panel/60 px-3 py-1">
        <span className="font-mono text-[10px] uppercase tracking-wide text-muted">
          {lang || 'code'}
        </span>
        <div className="ml-auto flex items-center gap-1.5">
          <CopyButton text={code} small />
          {needsToggle && (
            <button
              onClick={() => setOpen(!open)}
              className="rounded border border-border px-1.5 py-0.5 text-[10px] text-muted hover:text-fg"
            >
              {open ? 'Show less' : `Show all (${lines.length} lines)`}
            </button>
          )}
        </div>
      </div>
      <pre className="max-h-80 overflow-y-auto px-3 py-2 font-mono text-[11px] leading-relaxed text-fg/85 whitespace-pre-wrap break-words">
        {shown}
      </pre>
    </div>
  )
}

function Thought({ seconds, thinking, done }: { seconds: number | null; thinking: string; done: boolean }) {
  // Expanded while streaming ("Thinking"), auto-collapsed once finished ("Thought").
  const [open, setOpen] = useState(!done)
  useEffect(() => {
    if (done) setOpen(false)
  }, [done])
  const hasThinking = thinking && thinking.trim().length > 0
  return (
    <div className="rounded-lg border border-border bg-deep/40">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-muted hover:text-fg"
      >
        <span>💭</span>
        <span>{done ? 'Thought' : 'Thinking'}</span>
        {done && seconds != null && <span className="text-muted/60">· {seconds}s</span>}
        {hasThinking && <span className="ml-auto text-muted">{open ? '▾' : '▸'}</span>}
      </button>
      {open && hasThinking && (
        <div className="border-t border-border px-3 py-2 text-xs leading-relaxed text-muted whitespace-pre-wrap max-h-60 overflow-y-auto">
          {thinking}
        </div>
      )}
    </div>
  )
}

function EditedFiles({ files }: { files: { path: string; lang: string; summary: string }[] }) {
  const [open, setOpen] = useState(true)
  return (
    <div className="rounded-lg border border-border bg-deep/40">
      <button onClick={() => setOpen(!open)} className="flex w-full items-center justify-between px-3 py-1.5 text-xs text-muted hover:text-fg">
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

function Steps({ steps }: { steps: ToolStep[] }) {
  const groups: { kind: 'bash' | 'tool'; items: ToolStep[] }[] = []
  for (const s of steps) {
    const isBash = s.name === 'run_command'
    const last = groups[groups.length - 1]
    if (last && last.kind === (isBash ? 'bash' : 'tool')) last.items.push(s)
    else groups.push({ kind: isBash ? 'bash' : 'tool', items: [s] })
  }

  return (
    <div className="space-y-1.5">
      {groups.map((g, gi) =>
        g.kind === 'bash' ? <BashGroup key={gi} items={g.items} /> : <ToolRows key={gi} items={g.items} />,
      )}
    </div>
  )
}

function BashGroup({ items }: { items: ToolStep[] }) {
  const [open, setOpen] = useState(true)
  const failed = items.filter((s) => !s.ok).length
  return (
    <div className="rounded-lg border border-border bg-deep/40">
      <button onClick={() => setOpen(!open)} className="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-muted hover:text-fg">
        <span className={failed === 0 ? 'text-green-500' : 'text-red-400'}>{failed === 0 ? '✓' : '✗'}</span>
        <span>Ran commands {items.length}</span>
        <span className="ml-auto">{open ? '▾' : '▸'}</span>
      </button>
      {open && (
        <div className="border-t border-border">
          {items.map((s, i) => (
            <BashStep key={i} step={s} />
          ))}
        </div>
      )}
    </div>
  )
}

function BashStep({ step }: { step: ToolStep }) {
  const [open, setOpen] = useState(false)
  const d = step.detail
  const exitCode = (d?.exit_code as number | undefined) ?? 0
  const command = (d?.command as string) || ''
  const stdout = (d?.stdout as string) || ''
  const stderr = (d?.stderr as string) || ''

  return (
    <div className="border-t border-border first:border-t-0">
      <button onClick={() => setOpen(!open)} className="flex w-full items-center gap-2 px-3 py-1.5 text-xs hover:text-fg">
        <span className={step.ok ? 'text-green-500' : 'text-red-400'}>{step.ok ? '✓' : '✗'}</span>
        <span className="text-fg/90">used Bash</span>
        {!step.ok && <span className="text-red-400">exit {exitCode}</span>}
        <span className="text-muted">{step.durationSeconds}s</span>
        <span className="ml-auto text-muted">{open ? '▾' : '▸'}</span>
      </button>
      {open && (
        <div className="border-t border-border bg-ink/40 px-3 py-2 font-mono text-[11px] leading-relaxed max-h-60 overflow-y-auto overflow-x-hidden">
          {command && <div className="break-words text-fg/80"><span className="text-green-500">$ </span>{command}</div>}
          {stdout && <pre className="mt-1 whitespace-pre-wrap break-words text-fg/70">{stdout}</pre>}
          {stderr && <pre className="mt-1 whitespace-pre-wrap break-words text-red-300/80">{stderr}</pre>}
        </div>
      )}
    </div>
  )
}

function ToolRows({ items }: { items: ToolStep[] }) {
  const [open, setOpen] = useState(true)
  const failed = items.filter((s) => !s.ok).length
  return (
    <div className="rounded-lg border border-border bg-deep/40">
      <button onClick={() => setOpen(!open)} className="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-muted hover:text-fg">
        <span className={failed === 0 ? 'text-green-500' : 'text-red-400'}>{failed === 0 ? '✓' : '✗'}</span>
        <span>Ran {items.length} step{items.length === 1 ? '' : 's'}</span>
        <span className="ml-auto">{open ? '▾' : '▸'}</span>
      </button>
      {open && (
        <div className="border-t border-border">
          {items.map((s, i) => (
            <div key={i} className="flex items-center gap-2 px-3 py-1.5 text-xs text-fg/90">
              <span className={s.ok ? 'text-green-500' : 'text-red-400'}>{s.ok ? '✓' : '✗'}</span>
              <span className="truncate font-mono">{s.name}</span>
              {s.summary && s.summary !== 'running…' && <span className="ml-auto truncate text-muted">{s.summary}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
