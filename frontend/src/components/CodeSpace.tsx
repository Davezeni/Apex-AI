import Editor from '@monaco-editor/react'
import { useChat } from '../stores/useChat'

const EXT_LANG: Record<string, string> = {
  py: 'python', js: 'javascript', ts: 'typescript', tsx: 'typescript',
  jsx: 'javascript', json: 'json', md: 'markdown', html: 'html', css: 'css',
  yml: 'yaml', yaml: 'yaml', sh: 'shell', go: 'go', rs: 'rust', java: 'java',
  txt: 'plaintext',
}

const SAMPLE = `# hello.py
# Select a file from the Workspace tree to view it.
print("Hello from Apex AI")
`

export default function CodeSpace() {
  const activeFile = useChat((s) => s.activeFile)
  const fileContent = useChat((s) => s.fileContent)

  const content = fileContent || SAMPLE
  const lang = activeFile ? EXT_LANG[activeFile.split('.').pop() || ''] || 'plaintext' : 'python'

  return (
    <div className="flex h-full flex-col bg-surface">
      <div className="border-b border-border px-3 py-2 text-xs font-mono text-muted">
        {activeFile ? activeFile : 'workspace'}
      </div>
      <div className="min-h-0 flex-1">
        <Editor
          height="100%"
          language={lang}
          value={content}
          theme="vs-dark"
          options={{ minimap: { enabled: false }, fontSize: 13, readOnly: true, fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace' }}
        />
      </div>
    </div>
  )
}
