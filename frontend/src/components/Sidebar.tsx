// Sidebar: conversation list placeholder. Persistence lands in a later increment.
export default function Sidebar() {
  return (
    <aside className="hidden md:flex w-60 shrink-0 flex-col border-r border-border bg-panel">
      <div className="flex items-center gap-2 border-b border-border px-4 py-3">
        <span className="text-accent text-lg font-bold">Apex AI</span>
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
