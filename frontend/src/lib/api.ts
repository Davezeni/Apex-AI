// REST client for workspace + health endpoints (conversation CRUD comes later).

export async function fetchHealth(): Promise<Record<string, unknown>> {
  const res = await fetch('/health')
  return res.json()
}

export async function fetchFileTree(): Promise<Record<string, unknown>> {
  const res = await fetch('/api/workspace/tree')
  return res.json()
}
