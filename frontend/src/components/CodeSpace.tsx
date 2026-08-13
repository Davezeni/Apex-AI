// Code space: file tree + Monaco editor placeholder.
// The Monaco import is code-split so the editor does not inflate first paint.
import Editor from '@monaco-editor/react'

const SAMPLE = `# hello.py
# The agent will list real workspace files here in a later increment.
print("Hello from Apex AI")
`

export default function CodeSpace() {
  return (
    <div className="flex h-full">
      <div className="hidden sm:block w-44 shrink-0 overflow-y-auto border-r border-border bg-panel p-2 text-xs text-neutral-400">
        <p className="uppercase text-[10px] text-neutral-600 mb-1">workspace</p>
        <p className="font-mono">📄 hello.py</p>
      </div>
      <div className="flex-1">
        <Editor
          height="100%"
          defaultLanguage="python"
          defaultValue={SAMPLE}
          theme="vs-dark"
          options={{ minimap: { enabled: false }, fontSize: 13 }}
        />
      </div>
    </div>
  )
}
