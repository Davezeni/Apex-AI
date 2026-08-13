import { useState } from 'react'

export default function Header() {
  const [mode, setMode] = useState('Agent Mode')
  const [open, setOpen] = useState(false)

  const modes = ['Agent Mode', 'Chat Mode', 'Coder Mode']

  return (
    <header className="flex items-center gap-3 border-b border-border bg-panel px-3 py-2">
      <span className="text-fg font-semibold">Apex AI</span>

      {/* Mode dropdown */}
      <div className="relative">
        <button
          onClick={() => setOpen(!open)}
          className="flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-1.5 text-sm text-fg hover:border-muted"
        >
          {mode}
          <span className="text-muted">⌄</span>
        </button>
        {open && (
          <div className="absolute left-0 top-full z-40 mt-1 w-44 rounded-lg border border-border bg-panel py-1 shadow-lg">
            {modes.map((m) => (
              <button
                key={m}
                onClick={() => { setMode(m); setOpen(false) }}
                className={`block w-full px-3 py-1.5 text-left text-sm hover:bg-surface ${m === mode ? 'text-fg' : 'text-muted'}`}
              >
                {m}
              </button>
            ))}
          </div>
        )}
      </div>

    </header>
  )
}
