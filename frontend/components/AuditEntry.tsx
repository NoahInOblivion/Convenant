interface AuditEntryProps {
  eventType: string
  sessionId: string
  createdAt: string
  payload: Record<string, unknown>
}

export function AuditEntry({ eventType, sessionId, createdAt, payload }: AuditEntryProps) {
  return (
    <div className="border border-gray-800 rounded p-3 mb-2">
      <div className="flex items-center justify-between mb-2">
        <span className="font-mono text-xs text-accent">{eventType}</span>
        <span className="font-mono text-xs text-gray-500">{createdAt}</span>
      </div>
      <div className="text-xs text-gray-400 font-sans mb-1">Session: {sessionId}</div>
      <pre className="font-mono text-xs text-gray-300 overflow-auto max-h-24 bg-gray-950 p-2 rounded">
        {JSON.stringify(payload, null, 2)}
      </pre>
    </div>
  )
}
