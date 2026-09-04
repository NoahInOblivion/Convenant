type Status = 'approved' | 'rejected' | 'requires_human_approval' | 'pending'

const STATUS_STYLES: Record<Status, string> = {
  approved: 'bg-green-900 text-green-200 border border-green-700',
  rejected: 'bg-red-900 text-red-200 border border-red-700',
  requires_human_approval: 'bg-yellow-900 text-yellow-200 border border-yellow-700',
  pending: 'bg-gray-800 text-gray-300 border border-gray-600',
}

const STATUS_LABELS: Record<Status, string> = {
  approved: 'Approved',
  rejected: 'Rejected',
  requires_human_approval: 'Needs Approval',
  pending: 'Pending',
}

export function StatusBadge({ status }: { status: Status }) {
  const style = STATUS_STYLES[status] ?? STATUS_STYLES.pending
  const label = STATUS_LABELS[status] ?? status
  return (
    <span className={`inline-block px-2 py-1 text-xs font-sans rounded ${style}`}>
      {label}
    </span>
  )
}
