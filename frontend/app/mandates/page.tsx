import { MandateChip } from '@/components/MandateChip'
import { AmountDisplay } from '@/components/AmountDisplay'

export default function MandatesPage() {
  return (
    <div>
      <h1 className="text-2xl font-sans font-semibold mb-2">Mandate Chain</h1>
      <p className="text-sm text-gray-400 mb-6">
        Each purchase flows through a cryptographically-signed chain: Intent → Cart → Payment.
        Every link is HMAC-SHA256 signed and expiry-checked before proceeding.
      </p>
      <div className="border border-gray-800 rounded p-6 text-center text-gray-500 text-sm">
        Select a session to inspect its mandate chain.
      </div>

      {/* Mandate chain visualization placeholder */}
      <div className="mt-6 flex flex-col gap-3">
        <div className="border border-gray-800 rounded p-4 opacity-40">
          <div className="text-xs text-gray-500 font-sans mb-2">Example — Intent Mandate</div>
          <MandateChip mandateId="im-00000000-0000-0000-0000-000000000000" label="Intent" />
        </div>
        <div className="border border-gray-800 rounded p-4 opacity-40">
          <div className="text-xs text-gray-500 font-sans mb-2">Example — Cart Mandate</div>
          <MandateChip mandateId="cm-00000000-0000-0000-0000-000000000000" label="Cart" />
          <div className="mt-2"><AmountDisplay amount="4500.00" /></div>
        </div>
        <div className="border border-gray-800 rounded p-4 opacity-40">
          <div className="text-xs text-gray-500 font-sans mb-2">Example — Payment Mandate</div>
          <MandateChip mandateId="pm-00000000-0000-0000-0000-000000000000" label="Payment" />
        </div>
      </div>
    </div>
  )
}
