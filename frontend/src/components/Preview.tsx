// Preview pane: iframe that will render the sandboxed app via the backend proxy.
export default function Preview() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 text-neutral-500">
      <div className="text-3xl">👁️</div>
      <p className="text-sm">Live preview will render the app the agent builds.</p>
    </div>
  )
}
