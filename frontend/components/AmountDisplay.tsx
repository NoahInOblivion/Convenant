// Monetary values are always strings from the API — never parseFloat
export function AmountDisplay({ amount, currency = 'INR' }: { amount: string; currency?: string }) {
  return (
    <span className="font-mono text-sm text-accent">
      {currency} {amount}
    </span>
  )
}
