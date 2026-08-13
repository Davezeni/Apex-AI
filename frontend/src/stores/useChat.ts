import { create } from 'zustand'
import type { ChatMessage, Pane } from '../types'

interface ChatState {
  messages: ChatMessage[]
  activePane: Pane
  streaming: boolean
  setPane: (pane: Pane) => void
  addMessage: (msg: ChatMessage) => void
  /** append streamed text to the last assistant message (or create one) */
  appendDelta: (delta: string) => void
  appendStep: (step: { name: string; ok: boolean; summary: string }) => void
  finishMessage: () => void
  failMessage: (error: string) => void
  setStreaming: (v: boolean) => void
}

let nextId = 0
const uid = () => `m${++nextId}`

export const useChat = create<ChatState>((set) => ({
  messages: [],
  activePane: 'chat',
  streaming: false,

  setPane: (pane) => set({ activePane: pane }),

  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),

  appendDelta: (delta) =>
    set((s) => {
      const msgs = [...s.messages]
      const last = msgs[msgs.length - 1]
      if (last && last.role === 'assistant' && last.pending) {
        msgs[msgs.length - 1] = { ...last, text: last.text + delta }
      } else {
        msgs.push({ id: uid(), role: 'assistant', text: delta, steps: [], pending: true })
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
        msgs.push({ id: uid(), role: 'assistant', text: '', steps: [], error, pending: false })
      }
      return { messages: msgs, streaming: false }
    }),

  setStreaming: (v) => set({ streaming: v }),
}))
