import { useEffect, useState } from 'react'
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
  const renameConversation = useChat((s) => s.renameConversation)
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
            <ConversationRow
              key={c.id}
              conversation={c}
              active={c.id === currentId}
              onSelect={() => pick(c.id)}
              onDelete={() => deleteConversation(c.id)}
              onRename={(title) => renameConversation(c.id, title)}
            />
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

function ConversationRow({
  conversation, active, onSelect, onDelete, onRename,
}: {
  conversation: { id: string; title: string }
  active: boolean
  onSelect: () => void
  onDelete: () => void
  onRename: (title: string) => void
}) {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(conversation.title)

  const commit = () => {
    const t = value.trim()
    if (t && t !== conversation.title) onRename(t)
    else setValue(conversation.title)
    setEditing(false)
  }

  return (
    <div className={`group flex items-center rounded-lg ${active ? 'bg-surface' : 'hover:bg-surface/60'}`}>
      {editing ? (
        <input
          autoFocus
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => {
            if (e.key === 'Enter') commit()
            if (e.key === 'Escape') { setValue(conversation.title); setEditing(false) }
          }}
          className="min-w-0 flex-1 rounded bg-panel px-2 py-1.5 text-sm text-fg outline-none ring-1 ring-border"
        />
      ) : (
        <>
          <button
            onClick={onSelect}
            className="min-w-0 flex-1 truncate px-3 py-2 text-left text-sm text-fg/90"
          >
            {conversation.title}
          </button>
          <button
            onClick={() => setEditing(true)}
            title="Rename"
            aria-label="Rename conversation"
            className="mr-0.5 rounded p-1 text-muted opacity-0 transition-opacity hover:text-fg group-hover:opacity-100"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
            </svg>
          </button>
          <button
            onClick={onDelete}
            title="Delete"
            aria-label="Delete conversation"
            className="mr-1 rounded p-1 text-muted opacity-0 transition-opacity hover:text-red-400 group-hover:opacity-100"
          >
            ✕
          </button>
        </>
      )}
    </div>
  )
}
