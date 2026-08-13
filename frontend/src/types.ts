// Event types mirror the backend agent event stream (see backend/app/agent/events.py).

export type AgentEvent =
  | { type: 'TextDelta'; delta: string }
  | { type: 'ToolCallEvent'; name: string; arguments: Record<string, unknown> }
  | { type: 'ToolResultEvent'; name: string; ok: boolean; summary: string }
  | { type: 'Done'; text: string }
  | { type: 'Error'; message: string }

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  /** streamed assistant text */
  text: string
  /** tool steps for an assistant message */
  steps: { name: string; ok: boolean; summary: string }[]
  error?: string
  pending?: boolean
}

export type Pane = 'chat' | 'code' | 'preview'
