export function MandateChip({ mandateId, label }: { mandateId: string; label: string }) {
  return (
    <div className="inline-flex flex-col gap-1 px-3 py-2 bg-gray-900 border border-gray-700 rounded">
      <span className="text-xs text-gray-400 font-sans">{label}</span>
      <span className="font-mono text-xs text-gray-200 truncate max-w-48" title={mandateId}>
        {mandateId}
      </span>
    </div>
  )
}
