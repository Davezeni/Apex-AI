import { useEffect, useState } from 'react'
import { useChat } from '../stores/useChat'

interface TreeNode {
  name: string
  path: string
  type: 'file' | 'dir'
  children?: TreeNode[]
}

function buildTree(paths: string[]): TreeNode[] {
  const root: TreeNode = { name: 'workspace', path: '', type: 'dir', children: [] }
  for (const p of paths) {
    const parts = p.split('/')
    let node = root
    let acc = ''
    for (let i = 0; i < parts.length; i++) {
      acc = acc ? `${acc}/${parts[i]}` : parts[i]
      const isLast = i === parts.length - 1
      let child = node.children?.find((c) => c.name === parts[i])
      if (!child) {
        child = { name: parts[i], path: acc, type: isLast ? 'file' : 'dir', children: [] }
        node.children?.push(child)
      }
      node = child
    }
  }
  return root.children || []
}

export default function Workspace() {
  const [tree, setTree] = useState<TreeNode[]>([])
  const [showHidden, setShowHidden] = useState(false)
  const activeFile = useChat((s) => s.activeFile)
  const openFile = useChat((s) => s.openFile)

  useEffect(() => {
    fetch(`/api/workspace/tree${showHidden ? '?all=true' : ''}`)
      .then((r) => r.json())
      .then((files: string[]) => setTree(buildTree(files)))
      .catch(() => setTree([]))
  }, [showHidden])

  return (
    <div className="flex h-full flex-col bg-surface">
      <div className="flex items-center justify-between border-b border-border px-3 py-2">
        <span className="text-sm font-medium text-fg">Workspace</span>
        <label className="flex items-center gap-1.5 text-[11px] text-muted">
          <input
            type="checkbox"
            checked={showHidden}
            onChange={(e) => setShowHidden(e.target.checked)}
            className="h-3.5 w-3.5 accent-[#8A8884]"
          />
          Show hidden files
        </label>
      </div>
      <div className="flex-1 overflow-y-auto p-2 font-mono text-xs">
        {tree.length === 0 && <p className="p-2 text-muted">(empty workspace)</p>}
        <TreeNodes nodes={tree} active={activeFile} onOpen={openFile} depth={0} />
      </div>
    </div>
  )
}

function TreeNodes({ nodes, active, onOpen, depth }: { nodes: TreeNode[]; active: string | null; onOpen: (p: string) => void; depth: number }) {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({})

  return (
    <>
      {nodes.map((n) => {
        const pad = { paddingLeft: `${depth * 12 + 6}px` }
        if (n.type === 'dir') {
          const isClosed = collapsed[n.path]
          return (
            <div key={n.path}>
              <button
                onClick={() => setCollapsed((c) => ({ ...c, [n.path]: !c[n.path] }))}
                style={pad}
                className="flex w-full items-center gap-1 rounded py-1 text-left text-muted hover:text-fg"
              >
                <span>{isClosed ? '▸' : '▾'}</span>
                <span>📁 {n.name}</span>
              </button>
              {!isClosed && n.children && (
                <TreeNodes nodes={n.children} active={active} onOpen={onOpen} depth={depth + 1} />
              )}
            </div>
          )
        }
        return (
          <button
            key={n.path}
            onClick={() => onOpen(n.path)}
            style={pad}
            className={`flex w-full items-center gap-1 rounded py-1 text-left hover:bg-panel ${active === n.path ? 'bg-panel text-fg' : 'text-fg/80'}`}
          >
            <span className="opacity-0">▸</span>
            <span>📄 {n.name}</span>
          </button>
        )
      })}
    </>
  )
}
