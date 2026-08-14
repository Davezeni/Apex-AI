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
    const parts = p.split('/').filter(Boolean)
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
  // Sort folders first, then files, alphabetically (VS Code style).
  const sort = (nodes: TreeNode[]) =>
    nodes.sort((a, b) =>
      a.type !== b.type ? (a.type === 'dir' ? -1 : 1) : a.name.localeCompare(b.name),
    )
  const walk = (nodes: TreeNode[]) => {
    sort(nodes)
    nodes.forEach((n) => n.children && walk(n.children))
  }
  walk(root.children || [])
  return root.children || []
}

// Language → color (VS Code-ish palette) for the file icon dot.
function langColor(name: string): string {
  const ext = name.split('.').pop()?.toLowerCase() || ''
  const map: Record<string, string> = {
    py: '#3572A5', js: '#f1e05a', jsx: '#f1e05a', ts: '#3178c6', tsx: '#3178c6',
    json: '#cbcb41', md: '#519aba', html: '#e34c26', css: '#563d7c', yml: '#cb171e',
    yaml: '#cb171e', sh: '#89e051', go: '#00ADD8', rs: '#dea584', java: '#b07219',
    txt: '#8a8884', gitignore: '#8a8884',
  }
  return map[ext] || '#8a8884'
}

export default function Workspace() {
  const [tree, setTree] = useState<TreeNode[]>([])
  const [showHidden, setShowHidden] = useState(false)
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({})
  const activeFile = useChat((s) => s.activeFile)
  const openFile = useChat((s) => s.openFile)
  const workspaceTick = useChat((s) => s.workspaceTick)

  useEffect(() => {
    fetch(`/api/workspace/tree${showHidden ? '?all=true' : ''}`)
      .then((r) => r.json())
      .then((files: string[]) => setTree(buildTree(files)))
      .catch(() => setTree([]))
  }, [showHidden, workspaceTick])

  return (
    <div className="flex h-full flex-col bg-surface">
      <div className="flex items-center justify-between border-b border-border px-3 py-2">
        <span className="text-[11px] font-semibold uppercase tracking-wide text-muted">
          Explorer
        </span>
        <label className="flex items-center gap-1.5 text-[11px] text-muted">
          <input
            type="checkbox"
            checked={showHidden}
            onChange={(e) => setShowHidden(e.target.checked)}
            className="h-3.5 w-3.5 accent-[#8A8884]"
          />
          Show hidden
        </label>
      </div>
      <div className="flex-1 overflow-y-auto py-1 font-mono text-[13px]">
        {tree.length === 0 && <p className="px-3 py-2 text-xs text-muted/60">(empty workspace)</p>}
        <TreeNodes
          nodes={tree}
          active={activeFile}
          onOpen={openFile}
          depth={0}
          collapsed={collapsed}
          setCollapsed={setCollapsed}
        />
      </div>
    </div>
  )
}

function TreeNodes({
  nodes, active, onOpen, depth, collapsed, setCollapsed,
}: {
  nodes: TreeNode[]
  active: string | null
  onOpen: (p: string) => void
  depth: number
  collapsed: Record<string, boolean>
  setCollapsed: (fn: (c: Record<string, boolean>) => Record<string, boolean>) => void
}) {
  return (
    <>
      {nodes.map((n) => {
        const pad = { paddingLeft: `${depth * 14 + 8}px` }
        if (n.type === 'dir') {
          const isClosed = collapsed[n.path]
          return (
            <div key={n.path}>
              <button
                onClick={() => setCollapsed((c) => ({ ...c, [n.path]: !c[n.path] }))}
                style={pad}
                className="flex w-full items-center gap-1.5 rounded py-[3px] pr-2 text-left text-fg/90 hover:bg-panel"
              >
                <span className="text-muted w-3 text-[10px]">{isClosed ? '▸' : '▾'}</span>
                <FolderIcon open={!isClosed} />
                <span className="truncate">{n.name}</span>
              </button>
              {!isClosed && n.children && (
                <TreeNodes nodes={n.children} active={active} onOpen={onOpen} depth={depth + 1} collapsed={collapsed} setCollapsed={setCollapsed} />
              )}
            </div>
          )
        }
        return (
          <button
            key={n.path}
            onClick={() => onOpen(n.path)}
            style={pad}
            className={`flex w-full items-center gap-1.5 rounded py-[3px] pr-2 text-left ${
              active === n.path ? 'bg-panel text-fg' : 'text-fg/80 hover:bg-panel/60'
            }`}
          >
            <span className="w-3" />
            <FileIcon name={n.name} />
            <span className="truncate">{n.name}</span>
          </button>
        )
      })}
    </>
  )
}

function FolderIcon({ open }: { open: boolean }) {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill={open ? '#dcb67a' : '#a7865a'}>
      <path d="M10 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z" />
    </svg>
  )
}

function FileIcon({ name }: { name: string }) {
  const color = langColor(name)
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
      <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6z" fill="#3a3a3c" />
      <path d="M14 2v6h6" fill="none" stroke="#8a8884" strokeWidth="1" />
      <circle cx="9" cy="15" r="1.6" fill={color} />
      <circle cx="12" cy="18" r="1.6" fill={color} opacity="0.7" />
      <circle cx="15" cy="14" r="1.6" fill={color} opacity="0.9" />
    </svg>
  )
}
