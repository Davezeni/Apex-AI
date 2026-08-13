import { useChat } from '../stores/useChat'

interface Props {
  collapsed?: boolean
  hideToggle?: boolean
}

export default function Sidebar({ collapsed = false, hideToggle = false }: Props) {
  const toggleSidebar = useChat((s) => s.toggleSidebar)

  if (collapsed) {
    return (
      <aside className="hidden md:flex w-12 shrink-0 flex-col items-center border-r border-border bg-deep py-3">
        {!hideToggle && (
          <button
            onClick={toggleSidebar}
            title="Expand sidebar"
            aria-label="Expand sidebar"
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-surface text-muted transition-colors hover:border-muted hover:text-fg"
          >
            {/* clear panel-expand icon (two chevrons) */}
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="13 17 18 12 13 7" />
              <polyline points="6 17 11 12 6 7" />
            </svg>
          </button>
        )}
      </aside>
    )
  }

  return (
    <aside className={`flex h-full shrink-0 flex-col border-r border-border bg-deep ${hideToggle ? 'w-full' : 'w-60'}`}>
      {/* Brand */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <span className="text-fg text-base font-semibold">Apex AI</span>
        {!hideToggle && (
          <button
            onClick={toggleSidebar}
            title="Collapse sidebar"
            aria-label="Collapse sidebar"
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-border text-muted transition-colors hover:border-muted hover:text-fg"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="11 17 6 12 11 7" />
              <polyline points="18 17 13 12 18 7" />
            </svg>
          </button>
        )}
      </div>

      {/* Primary actions */}
      <div className="space-y-1 p-3">
        <button className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-left text-sm text-fg hover:border-muted">
          + New Chat
        </button>
        <button className="w-full rounded-lg px-3 py-2 text-left text-sm text-muted hover:bg-surface">
          🏆 Leaderboard
        </button>
        <button className="w-full rounded-lg px-3 py-2 text-left text-sm text-muted hover:bg-surface">
          🔍 Search
        </button>
      </div>

      <div className="border-t border-border" />

      {/* Conversation groups */}
      <div className="flex-1 overflow-y-auto p-3">
        <p className="text-[11px] uppercase tracking-wide text-muted">Today</p>
        <div className="mt-2 space-y-1">
          <button className="w-full truncate rounded-lg px-3 py-2 text-left text-sm text-fg/90 hover:bg-surface">
            Hey how can I create an AI app...
          </button>
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-border p-3">
        <p className="truncate text-xs text-muted">user@example.com</p>
        <p className="mt-2 text-[10px] text-muted/60">
          Terms of Use · Privacy Policy · Cookies
        </p>
      </div>
    </aside>
  )
}
