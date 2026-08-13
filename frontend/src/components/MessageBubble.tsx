import { useState } from 'react'
import type { ChatMessage, ToolStep } from '../types'

interface Props {
  message: ChatMessage
}

export default function MessageBubble({ message }: Props) {
  if (message.role === 'user') {
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
      {message.steps.length > 0 && <Steps steps={message.steps} />}
      {message.text && <p className="whitespace-pre-wrap text-sm leading-relaxed text-fg">{message.text}</p>}
      {message.pending && !message.text && <span className="text-muted text-sm animate-pulse">Thinking…</span>}
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
      <span>💭</span>
      <span>Thought for {seconds} second{seconds === 1 ? '' : 's'}</span>
      <span className="ml-1 text-muted">{open ? '▾' : '▸'}</span>
    </button>
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

/**
 * Render tool steps. Consecutive `run_command` steps are grouped into a
 * "Ran commands N" block; each bash command is a collapsible "used Bash · Xs"
 * with the command + output, and a green check (exit 0) or red ✗ (exit N).
 * Non-bash tools render as a row with a green/red checkmark.
 */
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
        <div className="border-t border-border bg-ink/40 px-3 py-2 font-mono text-[11px] leading-relaxed">
          {command && <div className="text-fg/80"><span className="text-green-500">$ </span>{command}</div>}
          {stdout && <pre className="mt-1 whitespace-pre-wrap text-fg/70">{stdout}</pre>}
          {stderr && <pre className="mt-1 whitespace-pre-wrap text-red-300/80">{stderr}</pre>}
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
