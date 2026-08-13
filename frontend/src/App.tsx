import { useChat } from './stores/useChat'
import Sidebar from './components/Sidebar'
import Chat from './components/Chat'
import CodeSpace from './components/CodeSpace'
import Preview from './components/Preview'
import type { Pane } from './types'

const TABS: { id: Pane; label: string; icon: string }[] = [
  { id: 'chat', label: 'Chat', icon: '💬' },
  { id: 'code', label: 'Code', icon: '📁' },
  { id: 'preview', label: 'Preview', icon: '👁️' },
]

export default function App() {
  const activePane = useChat((s) => s.activePane)
  const setPane = useChat((s) => s.setPane)
  const sidebarCollapsed = useChat((s) => s.sidebarCollapsed)
  const mobileMenuOpen = useChat((s) => s.mobileMenuOpen)
  const setMobileMenu = useChat((s) => s.setMobileMenu)

  return (
    <div className="flex h-full">
      {/* Desktop sidebar (collapsible to icon rail) */}
      <Sidebar collapsed={sidebarCollapsed} />

      {/* Desktop: multi-pane layout */}
      <div className="hidden md:flex flex-1 min-w-0">
        <main className="flex-1 min-w-0 border-r border-border">
          <Chat />
        </main>
        <section className="w-[38%] flex flex-col">
          <div className="h-1/2 border-b border-border">
            <CodeSpace />
          </div>
          <div className="h-1/2">
            <Preview />
          </div>
        </section>
      </div>

      {/* Mobile: header + slide-in drawer + single pane with bottom tabs */}
      <div className="flex flex-1 flex-col md:hidden">
        <header className="flex items-center gap-3 border-b border-border bg-panel px-3 py-2.5">
          <button
            onClick={() => setMobileMenu(true)}
            className="rounded-lg p-1.5 text-neutral-300 hover:bg-surface"
            title="Menu"
          >
            ☰
          </button>
          <span className="text-accent font-bold">Apex AI</span>
        </header>

        {mobileMenuOpen && (
          <>
            <div
              className="fixed inset-0 z-20 bg-black/50"
              onClick={() => setMobileMenu(false)}
            />
            <div className="fixed inset-y-0 left-0 z-30 w-64">
              <Sidebar hideToggle />
              <button
                onClick={() => setMobileMenu(false)}
                className="absolute top-2 right-2 rounded p-1 text-neutral-400 hover:text-white"
              >
                ✕
              </button>
            </div>
          </>
        )}

        <div className="flex-1 overflow-hidden">
          {activePane === 'chat' && <Chat />}
          {activePane === 'code' && <CodeSpace />}
          {activePane === 'preview' && <Preview />}
        </div>
        <nav className="flex border-t border-border bg-panel">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setPane(t.id)}
              className={`flex flex-1 flex-col items-center gap-0.5 py-2.5 text-xs ${
                activePane === t.id ? 'text-accent' : 'text-neutral-500'
              }`}
            >
              <span className="text-base">{t.icon}</span>
              {t.label}
            </button>
          ))}
        </nav>
      </div>
    </div>
  )
}
