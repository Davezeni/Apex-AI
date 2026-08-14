import { useEffect } from 'react'
import { useChat } from '../stores/useChat'

interface Props {
  collapsed?: boolean
  hideToggle?: boolean
}

export default function Sidebar({ collapsed = false, hideToggle = false }: Props) {
  const toggleSidebar = useChat((s) => s.toggleSidebar)
  const conversations = useChat((s) => s.conversations)
  const currentId = useChat((s) => s.currentId)
  const loadConversations = useChat((s) => s.loadConversations)
  const selectConversation = useChat((s) => s.selectConversation)
  const newConversation = useChat((s) => s.newConversation)
  const deleteConversation = useChat((s) => s.deleteConversation)
  const setMobileMenu = useChat((s) => s.setMobileMenu)

  useEffect(() => {
    loadConversations()
  }, [loadConversations])

  const pick = (id: string) => {
    selectConversation(id)
    setMobileMenu(false)
  }

  if (collapsed) {
    return (
      <aside className="hidden md:flex w-14 shrink-0 flex-col items-center border-r border-border bg-deep py-3">
        {!hideToggle && (
          <button
            onClick={toggleSidebar}
            title="Expand sidebar"
            aria-label="Expand sidebar"
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-surface text-fg shadow-sm transition-colors hover:border-muted hover:bg-panel"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
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
      {/* Brand + collapse */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <span className="text-fg text-base font-semibold">Apex AI</span>
        {!hideToggle && (
          <button
            onClick={toggleSidebar}
            title="Collapse sidebar"
            aria-label="Collapse sidebar"
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-border text-fg transition-colors hover:border-muted hover:bg-surface"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="11 17 6 12 11 7" />
              <polyline points="18 17 13 12 18 7" />
            </svg>
          </button>
        )}
      </div>

      {/* New chat */}
      <div className="p-3">
        <button
          onClick={newConversation}
          className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-left text-sm text-fg hover:border-muted"
        >
          + New Chat
        </button>
      </div>

      <div className="border-t border-border" />

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto p-3">
        <p className="text-[11px] uppercase tracking-wide text-muted">Conversations</p>
        <div className="mt-2 space-y-0.5">
          {conversations.length === 0 && (
            <p className="px-1 py-2 text-xs text-muted/60">No conversations yet</p>
          )}
          {conversations.map((c) => (
            <div
              key={c.id}
              className={`group flex items-center rounded-lg ${
                c.id === currentId ? 'bg-surface' : 'hover:bg-surface/60'
              }`}
            >
              <button
                onClick={() => pick(c.id)}
                className="min-w-0 flex-1 truncate px-3 py-2 text-left text-sm text-fg/90"
              >
                {c.title || 'Untitled'}
              </button>
              <button
                onClick={() => deleteConversation(c.id)}
                title="Delete"
                aria-label="Delete conversation"
                className="mr-1 rounded p-1 text-muted opacity-0 transition-opacity hover:text-red-400 group-hover:opacity-100"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-border p-3">
        <p className="mt-1 text-[10px] text-muted/60">
          Terms of Use · Privacy Policy · Cookies
        </p>
      </div>
    </aside>
  )
}
