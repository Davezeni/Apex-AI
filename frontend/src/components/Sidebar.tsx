import { useChat } from '../stores/useChat'

// Conversation list placeholder — persistence wiring lands in a later increment.
interface Props {
  /** When true, render as a narrow icon rail (desktop collapse). */
  collapsed?: boolean
  /** Hide the collapse/expand toggle (used inside the mobile drawer). */
  hideToggle?: boolean
}

export default function Sidebar({ collapsed = false, hideToggle = false }: Props) {
  const toggleSidebar = useChat((s) => s.toggleSidebar)

  if (collapsed) {
    return (
      <aside className="hidden md:flex w-14 shrink-0 flex-col items-center border-r border-border bg-panel py-3">
        {!hideToggle && (
          <button
            onClick={toggleSidebar}
            title="Expand sidebar"
            className="rounded-lg p-2 text-neutral-400 hover:bg-surface hover:text-white"
          >
            ▸
          </button>
        )}
        <div className="mt-3 flex flex-col gap-2 text-lg">
          <span title="New conversation">＋</span>
          <span title="Conversations">💬</span>
        </div>
      </aside>
    )
  }

  return (
    <aside className={`flex h-full shrink-0 flex-col border-r border-border bg-panel ${hideToggle ? 'w-full' : 'w-60'}`}>
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <span className="text-accent text-lg font-bold">Apex AI</span>
        {!hideToggle && (
          <button
            onClick={toggleSidebar}
            title="Collapse sidebar"
            className="rounded-lg p-1 text-neutral-400 hover:bg-surface hover:text-white"
          >
            ◂
          </button>
        )}
      </div>
      <button className="mx-3 mt-3 rounded-lg border border-border bg-surface px-3 py-2 text-sm hover:border-accent">
        + New conversation
      </button>
      <div className="flex-1 overflow-y-auto p-3 text-sm text-neutral-500">
        <p className="text-xs uppercase tracking-wide text-neutral-600">Conversations</p>
        <p className="mt-2 text-xs">(coming soon)</p>
      </div>
    </aside>
  )
}
