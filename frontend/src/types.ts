// Event types mirror the backend agent event stream (see backend/app/agent/events.py).

export type AgentEvent =
  | { type: 'TextDelta'; delta: string }
  | { type: 'Thinking'; text: string }
  | { type: 'ToolCallEvent'; name: string; arguments: Record<string, unknown> }
  | { type: 'ToolResultEvent'; name: string; ok: boolean; summary: string; durationSeconds: number; detail: Record<string, unknown> }
  | { type: 'Review'; text: string }
  | { type: 'Done'; text: string }
  | { type: 'Error'; message: string }

export interface FileChange {
  path: string
  lang: string
  summary: string
}

export interface ToolStep {
  name: string
  ok: boolean
  summary: string
  durationSeconds: number
  detail: Record<string, unknown>
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  text: string
  steps: ToolStep[]
  /** files touched by the assistant turn */
  files: FileChange[]
  /** thinking duration in seconds (for "Thought for Xs") */
  thoughtSeconds: number | null
  /** actual chain-of-thought / reasoning text from the model */
  thinking: string
  /** review critique from the reviewer agent */
  review?: string
  error?: string
  pending?: boolean
}

export type Pane = 'chat' | 'code' | 'preview'
