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

  return (
    <div className="flex h-full">
      <Sidebar />

      {/* Desktop: multi-pane layout */}
      <div className="hidden md:flex flex-1">
        <main className="flex-1 border-r border-border">
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

      {/* Mobile: single pane driven by bottom tabs */}
      <div className="flex flex-1 flex-col md:hidden">
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
              className={`flex-1 flex flex-col items-center gap-0.5 py-2.5 text-xs ${
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
