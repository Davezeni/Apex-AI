import { useEffect, useState } from 'react'

interface PreviewState {
  mode: string
  url: string | null
  port: number | null
}

export default function Preview() {
  const [state, setState] = useState<PreviewState>({ mode: 'none', url: null, port: null })
  const [loading, setLoading] = useState(false)

  const load = () => {
    setLoading(true)
    fetch('/api/preview')
      .then((r) => r.json())
      .then((s: PreviewState) => setState(s))
      .catch(() => setState({ mode: 'none', url: null, port: null }))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

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
            No preview yet. Ask the agent to build a web app, then it will
            appear here — or tap below to preview static files.
          </p>
          <button
            onClick={() => {
              fetch('/api/preview/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mode: 'static' }),
              }).then(load)
            }}
            className="rounded-lg border border-border bg-panel px-3 py-2 text-xs text-fg hover:border-muted"
          >
            Start static preview
          </button>
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
          <iframe
            key={state.url || 'preview'}
            src={state.url || undefined}
            className="flex-1 w-full border-0 bg-white"
            title="Live preview"
          />
        </>
      )}
      {loading && <div className="text-center text-xs text-muted py-1">Loading…</div>}
    </div>
  )
}
