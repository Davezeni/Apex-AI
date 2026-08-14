import { useEffect, useState } from 'react'
import { useChat } from '../stores/useChat'

interface PreviewState {
  mode: string
  url: string | null
  port: number | null
}

export default function Preview() {
  const [state, setState] = useState<PreviewState>({ mode: 'none', url: null, port: null })
  const [loading, setLoading] = useState(false)
  const workspaceTick = useChat((s) => s.workspaceTick)

  const load = () => {
    setLoading(true)
    fetch('/api/preview')
      .then((r) => r.json())
      .then((s: PreviewState) => setState(s))
      .catch(() => setState({ mode: 'none', url: null, port: null }))
      .finally(() => setLoading(false))
  }

  // Auto-refresh when the workspace changes (agent writes files) or on mount.
  useEffect(load, [workspaceTick])

  const fullUrl = state.url ? `${location.origin}${state.url}` : null

  return (
    <div className="flex h-full flex-col bg-surface">
      <div className="flex items-center justify-between border-b border-border px-3 py-2">
        <span className="text-sm font-medium text-fg">Preview</span>
        <button onClick={load} className="rounded border border-border px-2 py-1 text-xs text-muted hover:border-muted hover:text-fg">
          ↻ Refresh
        </button>
      </div>

      {state.mode === 'none' ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 p-4 text-center text-muted">
          <div className="text-3xl">👁️</div>
          <p className="text-sm">
            No preview yet. Ask the agent to build a web page — it will write an
            <span className="font-mono text-fg/80"> index.html </span>
            and it will appear here automatically.
          </p>
        </div>
      ) : (
        <>
          {fullUrl && (
            <div className="flex items-center gap-2 border-b border-border bg-panel px-3 py-1.5 text-xs">
              <span className="text-muted">🔗</span>
              <a href={fullUrl} target="_blank" rel="noreferrer" className="truncate text-fg underline">
                {fullUrl}
              </a>
              <button
                onClick={() => navigator.clipboard?.writeText(fullUrl)}
                className="ml-auto rounded border border-border px-1.5 py-0.5 text-[10px] text-muted hover:text-fg"
              >
                Copy
              </button>
            </div>
          )}
          {/* key includes workspaceTick so the iframe reloads when files change */}
          <iframe
            key={workspaceTick}
            src={state.url || undefined}
            className="flex-1 w-full border-0 bg-white"
            title="Live preview"
          />
        </>
      )}
      {loading && <div className="py-1 text-center text-xs text-muted">Loading…</div>}
    </div>
  )
}
