'use client'
import { useState } from 'react'
import { StatusBadge } from '@/components/StatusBadge'
import { AmountDisplay } from '@/components/AmountDisplay'

interface CartItem {
  sku: string
  name: string
  quantity: number
  agent_proposed_price: string
  verified_price: string | null
}

interface ProposalResult {
  proposal_id: string
  decision: 'approved' | 'rejected' | 'requires_human_approval'
  verified_total: string
  reason: string
  items: CartItem[]
}

export default function HomePage() {
  const [request, setRequest] = useState('I need a mechanical keyboard and an ergonomic mouse under ₹6500')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ProposalResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!request.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res = await fetch('/api/propose', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ request, session_id: crypto.randomUUID() }),
      })
      if (!res.ok) throw new Error(`API error: ${res.status}`)
      const data = await res.json()
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-sans font-semibold mb-2">New Purchase Request</h1>
      <p className="text-sm text-gray-400 mb-6">Describe what you need. The agent will propose a cart for review.</p>

      <form onSubmit={handleSubmit} className="mb-8">
        <textarea
          value={request}
          onChange={e => setRequest(e.target.value)}
          placeholder="e.g. I need a keyboard and mouse under ₹6000"
          rows={3}
          className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm font-sans text-gray-100 placeholder-gray-500 focus:outline-none focus:border-accent resize-none"
        />
        <button
          type="submit"
          disabled={loading || !request.trim()}
          className="mt-3 px-4 py-2 bg-accent hover:bg-accent-hover text-white text-sm font-sans rounded disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? 'Processing…' : 'Submit Request'}
        </button>
      </form>

      {error && (
        <div className="border border-red-800 bg-red-950 rounded p-3 text-sm text-red-300 mb-4">{error}</div>
      )}

      {result && (
        <div className="border border-gray-800 rounded p-4">
          <div className="flex items-center gap-3 mb-4">
            <StatusBadge status={result.decision} />
            <AmountDisplay amount={result.verified_total} />
          </div>
          <p className="text-sm text-gray-400 mb-4">{result.reason}</p>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-gray-500 border-b border-gray-800">
                <th className="text-left pb-2 font-sans">SKU</th>
                <th className="text-left pb-2 font-sans">Name</th>
                <th className="text-right pb-2 font-sans">Qty</th>
                <th className="text-right pb-2 font-sans">Price (verified)</th>
              </tr>
            </thead>
            <tbody>
              {result.items.map(item => (
                <tr key={item.sku} className="border-b border-gray-900">
                  <td className="py-2 font-mono text-xs text-gray-300">{item.sku}</td>
                  <td className="py-2 font-sans text-sm">{item.name}</td>
                  <td className="py-2 text-right font-mono text-xs">{item.quantity}</td>
                  <td className="py-2 text-right">
                    <AmountDisplay amount={item.verified_price ?? item.agent_proposed_price} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
