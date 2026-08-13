import { create } from 'zustand'
import type { ChatMessage, FileChange, Pane, ToolStep } from '../types'

interface ChatState {
  messages: ChatMessage[]
  activePane: Pane
  streaming: boolean
  sidebarCollapsed: boolean
  mobileMenuOpen: boolean
  activeFile: string | null
  fileContent: string
  setPane: (pane: Pane) => void
  toggleSidebar: () => void
  setMobileMenu: (open: boolean) => void
  openFile: (path: string) => Promise<void>
  addMessage: (msg: ChatMessage) => void
  appendDelta: (delta: string) => void
  appendStep: (step: ToolStep) => void
  markFile: (file: FileChange) => void
  setThought: (seconds: number) => void
  setThinking: (thinking: string) => void
  finishMessage: () => void
  failMessage: (error: string) => void
  setStreaming: (v: boolean) => void
}

let nextId = 0
const uid = () => `m${++nextId}`

const LANG_OF = (path: string) =>
  ({ py: 'PYTHON', js: 'JAVASCRIPT', ts: 'TYPESCRIPT', tsx: 'TYPESCRIPT', jsx: 'JAVASCRIPT',
    json: 'JSON', md: 'MARKDOWN', html: 'HTML', css: 'CSS', yml: 'YAML', yaml: 'YAML',
    sh: 'SHELL', txt: 'PLAIN', go: 'GO', rs: 'RUST', java: 'JAVA' })[path.split('.').pop() || ''] || 'PLAIN'

export const useChat = create<ChatState>((set) => ({
  messages: [],
  activePane: 'chat',
  streaming: false,
  sidebarCollapsed: false,
  mobileMenuOpen: false,
  activeFile: null,
  fileContent: '',

  setPane: (pane) => set({ activePane: pane, mobileMenuOpen: false }),
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  setMobileMenu: (open) => set({ mobileMenuOpen: open }),

  openFile: async (path) => {
    set({ activeFile: path })
    try {
      const r = await fetch(`/api/workspace/file?path=${encodeURIComponent(path)}`)
      if (r.ok) set({ fileContent: (await r.json()).content })
      else set({ fileContent: `// unable to read ${path}` })
    } catch {
      set({ fileContent: `// error loading ${path}` })
    }
  },

  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),

  appendDelta: (delta) =>
    set((s) => {
      const msgs = [...s.messages]
      const last = msgs[msgs.length - 1]
      if (last && last.role === 'assistant' && last.pending) {
        msgs[msgs.length - 1] = { ...last, text: last.text + delta }
      } else {
        msgs.push({ id: uid(), role: 'assistant', text: delta, steps: [], files: [], thoughtSeconds: null, thinking: "", pending: true })
      }
      return { messages: msgs }
    }),

  appendStep: (step) =>
    set((s) => {
      const msgs = [...s.messages]
      const last = msgs[msgs.length - 1]
      if (last && last.role === 'assistant') {
        msgs[msgs.length - 1] = { ...last, steps: [...last.steps, step] }
      }
      return { messages: msgs }
    }),

  markFile: (file) =>
    set((s) => {
      const msgs = [...s.messages]
      const last = msgs[msgs.length - 1]
      if (!last || last.role !== 'assistant') return { messages: msgs }
      const exists = last.files.some((f) => f.path === file.path)
      const files = exists
        ? last.files.map((f) => (f.path === file.path ? { ...f, ...file } : f))
        : [...last.files, { ...file, lang: file.lang || LANG_OF(file.path) }]
      msgs[msgs.length - 1] = { ...last, files }
      return { messages: msgs }
    }),

  setThought: (seconds) =>
    set((s) => {
      const msgs = [...s.messages]
      const last = msgs[msgs.length - 1]
      if (last && last.role === 'assistant') {
        msgs[msgs.length - 1] = { ...last, thoughtSeconds: seconds }
      }
      return { messages: msgs }
    }),

  setThinking: (thinking) =>
    set((s) => {
      const msgs = [...s.messages]
      const last = msgs[msgs.length - 1]
      if (last && last.role === 'assistant') {
        msgs[msgs.length - 1] = { ...last, thinking }
      }
      return { messages: msgs }
    }),

  finishMessage: () =>
    set((s) => {
      const msgs = [...s.messages]
      const last = msgs[msgs.length - 1]
      if (last && last.role === 'assistant') {
        msgs[msgs.length - 1] = { ...last, pending: false }
      }
      return { messages: msgs, streaming: false }
    }),

  failMessage: (error) =>
    set((s) => {
      const msgs = [...s.messages]
      const last = msgs[msgs.length - 1]
      if (last && last.role === 'assistant') {
        msgs[msgs.length - 1] = { ...last, pending: false, error }
      } else {
        msgs.push({ id: uid(), role: 'assistant', text: '', steps: [], files: [], thoughtSeconds: null, thinking: "", error, pending: false })
      }
      return { messages: msgs, streaming: false }
    }),

  setStreaming: (v) => set({ streaming: v }),
}))
