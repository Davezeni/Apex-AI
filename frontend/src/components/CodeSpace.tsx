import { useEffect, useState } from 'react'
import Editor from '@monaco-editor/react'

const EXT_LANG: Record<string, string> = {
  py: 'python', js: 'javascript', ts: 'typescript', tsx: 'typescript',
  jsx: 'javascript', json: 'json', md: 'markdown', html: 'html', css: 'css',
  yml: 'yaml', yaml: 'yaml', sh: 'shell', txt: 'plaintext',
}

const SAMPLE = `# hello.py
# Select a file from the tree to view it, or ask the agent to create files.
print("Hello from Apex AI")
`

export default function CodeSpace() {
  const [tree, setTree] = useState<string[]>([])
  const [showTree, setShowTree] = useState(true)
  const [active, setActive] = useState<string | null>(null)
  const [content, setContent] = useState(SAMPLE)

  useEffect(() => {
    fetch('/api/workspace/tree')
      .then((r) => r.json())
      .then((files: string[]) => setTree(files))
      .catch(() => setTree([]))
  }, [])

  const openFile = async (path: string) => {
    setActive(path)
    try {
      const r = await fetch(`/api/workspace/file?path=${encodeURIComponent(path)}`)
      if (r.ok) {
        const data = await r.json()
        setContent(data.content)
      } else {
        setContent(`// unable to read ${path}`)
      }
    } catch {
      setContent(`// error loading ${path}`)
    }
    // On small screens, auto-hide the tree after picking a file.
    if (window.innerWidth < 640) setShowTree(false)
  }

  const lang = active ? EXT_LANG[active.split('.').pop() || ''] || 'plaintext' : 'python'

  return (
    <div className="flex h-full">
      {showTree && (
        <div className="flex h-full w-44 shrink-0 flex-col border-r border-border bg-panel">
          <div className="flex items-center justify-between px-2 py-1.5 text-[10px] uppercase text-neutral-600">
            <span>workspace</span>
            <button
              onClick={() => setShowTree(false)}
              className="rounded px-1 text-neutral-500 hover:text-white"
              title="Hide file tree"
            >
              ◂
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-2 text-xs text-neutral-400">
            {tree.length === 0 && <p className="text-neutral-600">(empty)</p>}
            {tree.map((f) => (
              <button
                key={f}
                onClick={() => openFile(f)}
                className={`block w-full truncate rounded px-1.5 py-1 text-left font-mono hover:bg-surface ${
                  active === f ? 'bg-surface text-white' : ''
                }`}
              >
                📄 {f}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        {!showTree && (
          <button
            onClick={() => setShowTree(true)}
            className="mb-1 self-start rounded px-2 py-1 text-xs text-neutral-400 hover:text-white"
            title="Show file tree"
          >
            ▸ files
          </button>
        )}
        <div className="min-h-0 flex-1">
          <Editor
            height="100%"
            language={lang}
            value={content}
            theme="vs-dark"
            options={{ minimap: { enabled: false }, fontSize: 13, readOnly: true }}
          />
        </div>
      </div>
    </div>
  )
}
