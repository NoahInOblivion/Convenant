import { AuditEntry } from '@/components/AuditEntry'

const PLACEHOLDER_ENTRIES = [
  {
    eventType: 'proposal_received',
    sessionId: 'ses-example',
    createdAt: '2026-09-04T10:00:00Z',
    payload: { proposal_id: 'prop-example', items: 1 },
  },
  {
    eventType: 'policy_decision',
    sessionId: 'ses-example',
    createdAt: '2026-09-04T10:00:01Z',
    payload: { decision: 'approved', verified_total: '4500.00' },
  },
  {
    eventType: 'mandate_signed',
    sessionId: 'ses-example',
    createdAt: '2026-09-04T10:00:02Z',
    payload: { mandate_type: 'intent', mandate_id: 'im-example' },
  },
]

export default function AuditPage() {
  return (
    <div>
      <h1 className="text-2xl font-sans font-semibold mb-2">Audit Log</h1>
      <p className="text-sm text-gray-400 mb-6">
        Every proposal, policy decision, mandate signature, and payment is recorded here.
        Entries are immutable — no UPDATE or DELETE possible.
      </p>
      <div className="mb-4">
        {PLACEHOLDER_ENTRIES.map((entry, i) => (
          <AuditEntry key={i} {...entry} />
        ))}
      </div>
    </div>
  )
}
