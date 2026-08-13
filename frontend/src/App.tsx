import { useChat } from './stores/useChat'
import Header from './components/Header'
import Sidebar from './components/Sidebar'
import Chat from './components/Chat'
import Workspace from './components/Workspace'
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
    <div className="flex h-full flex-col bg-deep">
      <Header />

      <div className="flex min-h-0 flex-1">
        {/* Left sidebar (desktop) */}
        <Sidebar collapsed={sidebarCollapsed} />

        {/* Desktop: chat + workspace panel */}
        <div className="hidden md:flex flex-1 min-w-0">
          <main className="flex-1 min-w-0 border-r border-border">
            <Chat />
          </main>
          {/* Right: workspace (file tree) + code editor */}
          <section className="w-[34%] flex flex-col border-r border-border">
            <div className="h-[45%] border-b border-border">
              <Workspace />
            </div>
            <div className="h-[55%]">
              <CodeSpace />
            </div>
          </section>
        </div>

        {/* Mobile: single pane with bottom tabs */}
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

          <div className="flex-1 overflow-hidden">
            {activePane === 'chat' && <Chat />}
            {activePane === 'code' && <Workspace />}
            {activePane === 'preview' && <Preview />}
          </div>
          <nav className="flex border-t border-border bg-panel">
            {TABS.map((t) => (
              <button
                key={t.id}
                onClick={() => setPane(t.id)}
                className={`flex flex-1 flex-col items-center gap-0.5 py-2.5 text-xs ${activePane === t.id ? 'text-fg' : 'text-muted'}`}
              >
                <span className="text-base">{t.icon}</span>
                {t.label}
              </button>
            ))}
          </nav>
        </div>
      </div>
    </div>
  )
}
