import { create } from 'zustand'
import type { ChatMessage, FileChange, Pane, ToolStep } from '../types'

export interface Conversation {
  id: string
  title: string
  updated_at: number
}

interface ChatState {
  messages: ChatMessage[]
  activePane: Pane
  streaming: boolean
  sidebarCollapsed: boolean
  mobileMenuOpen: boolean
  activeFile: string | null
  fileContent: string
  /** increments when the workspace may have changed (files written/agent done) */
  workspaceTick: number
  conversations: Conversation[]
  currentId: string | null
  setPane: (pane: Pane) => void
  toggleSidebar: () => void
  setMobileMenu: (open: boolean) => void
  openFile: (path: string) => Promise<void>
  closeFile: () => void
  bumpWorkspace: () => void
  loadConversations: () => Promise<void>
  selectConversation: (id: string) => Promise<void>
  newConversation: () => Promise<void>
  deleteConversation: (id: string) => Promise<void>
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
  workspaceTick: 0,
  conversations: [],
  currentId: null,

  setPane: (pane) => set({ activePane: pane, mobileMenuOpen: false }),
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  setMobileMenu: (open) => set({ mobileMenuOpen: open }),
  bumpWorkspace: () => set((s) => ({ workspaceTick: s.workspaceTick + 1 })),

  loadConversations: async () => {
    try {
      const r = await fetch('/api/conversations')
      const convs = (await r.json()) as Conversation[]
      set({ conversations: convs })
    } catch {
      /* ignore */
    }
  },

  selectConversation: async (id) => {
    try {
      const r = await fetch(`/api/conversations/${id}`)
      const conv = await r.json()
      const msgs = (conv.messages || [])
        .filter((m: { role: string; content: string }) => m.content && m.content.trim())
        .map((m: { id: string; role: string; content: string }) => ({
          id: m.id,
          role: m.role === 'user' ? 'user' : 'assistant',
          text: m.content,
          steps: [],
          files: [],
          thoughtSeconds: null,
          thinking: '',
          pending: false,
        }))
      set({ messages: msgs, currentId: id })
    } catch {
      /* ignore */
    }
  },

  newConversation: async () => {
    try {
      const r = await fetch('/api/conversations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'New conversation' }),
      })
      const conv = await r.json()
      set({ messages: [], currentId: conv.id })
      await useChat.getState().loadConversations()
    } catch {
      /* ignore */
    }
  },

  deleteConversation: async (id) => {
    try {
      await fetch(`/api/conversations/${id}`, { method: 'DELETE' })
      const next = useChat.getState()
      if (next.currentId === id) {
        set({ currentId: null, messages: [] })
      }
      await useChat.getState().loadConversations()
    } catch {
      /* ignore */
    }
  },

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

  closeFile: () => set({ activeFile: null, fileContent: '' }),

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
