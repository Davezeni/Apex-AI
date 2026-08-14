import { useEffect } from 'react'
import { useChat } from './stores/useChat'
import { setConversationId } from './lib/ws'
import Sidebar from './components/Sidebar'
import Chat from './components/Chat'
import Workspace from './components/Workspace'
import CodeSpace from './components/CodeSpace'
import Preview from './components/Preview'
import type { Pane } from './types'

const TABS: { id: Pane; icon: string; title: string }[] = [
  { id: 'chat', icon: '💬', title: 'Chat' },
  { id: 'code', icon: '📁', title: 'Code' },
  { id: 'preview', icon: '👁️', title: 'Preview' },
]

export default function App() {
  const activePane = useChat((s) => s.activePane)
  const setPane = useChat((s) => s.setPane)
  const sidebarCollapsed = useChat((s) => s.sidebarCollapsed)
  const mobileMenuOpen = useChat((s) => s.mobileMenuOpen)
  const setMobileMenu = useChat((s) => s.setMobileMenu)

  // Ensure a conversation exists so the backend can persist memory.
  useEffect(() => {
    fetch('/api/conversations')
      .then((r) => r.json())
      .then((convs: { id: string }[]) => {
        if (convs.length > 0) {
          setConversationId(convs[0].id)
        } else {
          fetch('/api/conversations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: 'New conversation' }),
          })
            .then((r) => r.json())
            .then((c: { id: string }) => setConversationId(c.id))
        }
      })
      .catch(() => {})
  }, [])

  return (
    <div className="flex h-full flex-col bg-deep">
      <div className="flex min-h-0 flex-1">
        {/* Left sidebar (desktop) */}
        <Sidebar collapsed={sidebarCollapsed} />

        {/* Desktop: chat + workspace panel */}
        <div className="hidden md:flex flex-1 min-w-0">
          <main className="flex-1 min-w-0 border-r border-border">
            <Chat />
          </main>
          <section className="w-[34%] flex flex-col border-r border-border">
            <div className="h-[45%] border-b border-border">
              <Workspace />
            </div>
            <div className="h-[55%]">
              <CodeSpace />
            </div>
          </section>
        </div>

        {/* Mobile: slim top bar + icon tabs + single pane */}
        <div className="flex flex-1 flex-col md:hidden">
          {mobileMenuOpen && (
            <>
              <div className="fixed inset-0 z-20 bg-black/50" onClick={() => setMobileMenu(false)} />
              <div className="fixed inset-y-0 left-0 z-30 w-64">
                <Sidebar hideToggle />
                <button onClick={() => setMobileMenu(false)} className="absolute top-2 right-2 rounded p-1 text-muted hover:text-fg">✕</button>
              </div>
            </>
          )}

          {/* Top bar: hamburger + brand */}
          <div className="flex items-center gap-2 border-b border-border bg-panel px-3 py-2">
            <button
              onClick={() => setMobileMenu(true)}
              title="Menu"
              className="rounded-lg p-1.5 text-fg hover:bg-surface"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <line x1="3" y1="6" x2="21" y2="6" />
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="3" y1="18" x2="21" y2="18" />
              </svg>
            </button>
            <span className="text-fg font-semibold">Apex AI</span>
          </div>

          {/* Icon-only tabs */}
          <nav className="flex border-b border-border bg-panel">
            {TABS.map((t) => (
              <button
                key={t.id}
                onClick={() => setPane(t.id)}
                title={t.title}
                aria-label={t.title}
                className={`flex flex-1 items-center justify-center py-2 text-base ${activePane === t.id ? 'text-fg border-b-2 border-fg' : 'text-muted border-b-2 border-transparent'}`}
              >
                {t.icon}
              </button>
            ))}
          </nav>

          <div className="flex-1 overflow-hidden">
            {activePane === 'chat' && <Chat />}
            {activePane === 'code' && <MobileCodePane />}
            {activePane === 'preview' && <Preview />}
          </div>
        </div>
      </div>
    </div>
  )
}

/** Mobile code pane: file tree → tap a file → editor, with a back button. */
function MobileCodePane() {
  const activeFile = useChat((s) => s.activeFile)
  const closeFile = useChat((s) => s.closeFile)

  if (activeFile) {
    return (
      <div className="flex h-full flex-col">
        <div className="flex items-center gap-2 border-b border-border bg-panel px-3 py-1.5">
          <button onClick={closeFile} className="rounded px-2 py-1 text-xs text-muted hover:text-fg">
            ← Files
          </button>
          <span className="truncate text-xs font-mono text-fg/80">{activeFile}</span>
        </div>
        <div className="min-h-0 flex-1">
          <CodeSpace />
        </div>
      </div>
    )
  }
  return <Workspace />
}
