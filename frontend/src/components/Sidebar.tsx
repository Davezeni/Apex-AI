import { useChat } from '../stores/useChat'

interface Props {
  collapsed?: boolean
  hideToggle?: boolean
}

export default function Sidebar({ collapsed = false, hideToggle = false }: Props) {
  const toggleSidebar = useChat((s) => s.toggleSidebar)

  if (collapsed) {
    return (
      <aside className="hidden md:flex w-14 shrink-0 flex-col items-center border-r border-border bg-deep py-3">
        {!hideToggle && (
          <button onClick={toggleSidebar} className="rounded-lg p-2 text-muted hover:bg-surface hover:text-fg">▸</button>
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
          <button onClick={toggleSidebar} className="rounded-lg p-1 text-muted hover:bg-surface hover:text-fg">◂</button>
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
