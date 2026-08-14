import Editor from '@monaco-editor/react'
import { useChat } from '../stores/useChat'

const EXT_LANG: Record<string, string> = {
  py: 'python', js: 'javascript', ts: 'typescript', tsx: 'typescript',
  jsx: 'javascript', json: 'json', md: 'markdown', html: 'html', css: 'css',
  yml: 'yaml', yaml: 'yaml', sh: 'shell', go: 'go', rs: 'rust', java: 'java',
  txt: 'plaintext', gitignore: 'plaintext',
}

const SAMPLE = `# No file open
# Select a file from the Explorer to view it here.
`

export default function CodeSpace() {
  const activeFile = useChat((s) => s.activeFile)
  const fileContent = useChat((s) => s.fileContent)
  const closeFile = useChat((s) => s.closeFile)

  const content = fileContent || SAMPLE
  const lang = activeFile ? EXT_LANG[activeFile.split('.').pop() || ''] || 'plaintext' : 'plaintext'
  const fileName = activeFile?.split('/').pop() || ''

  return (
    <div className="flex h-full flex-col bg-surface">
      {/* Tab bar (VS Code style) */}
      <div className="flex items-center border-b border-border bg-panel">
        {activeFile ? (
          <div className="flex items-center gap-2 border-r border-border bg-surface px-3 py-1.5">
            <span className="font-mono text-xs text-fg">{fileName}</span>
            <span className="rounded bg-panel px-1 py-0.5 font-mono text-[9px] uppercase tracking-wide text-muted">
              {lang}
            </span>
            <button
              onClick={closeFile}
              title="Close file"
              className="ml-1 rounded px-1 text-muted hover:bg-panel hover:text-fg"
            >
              ✕
            </button>
          </div>
        ) : (
          <div className="px-3 py-1.5 text-xs text-muted">No file open</div>
        )}
        {/* breadcrumb */}
        {activeFile && (
          <div className="ml-2 hidden truncate font-mono text-[11px] text-muted sm:block">
            {activeFile}
          </div>
        )}
      </div>

      {/* Editor */}
      <div className="min-h-0 flex-1">
        <Editor
          height="100%"
          language={lang}
          value={content}
          theme="vs-dark"
          options={{
            minimap: { enabled: true, maxColumn: 80 },
            fontSize: 13,
            readOnly: true,
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
            lineNumbers: 'on',
            scrollBeyondLastLine: false,
            automaticLayout: true,
            padding: { top: 8 },
          }}
        />
      </div>
    </div>
  )
}
