const CATALOG = [
  { sku: 'LAPTOP001', name: 'ProBook Laptop 14', price: '75000.00', stock: 10 },
  { sku: 'LAPTOP002', name: 'UltraSlim Laptop 15', price: '95000.00', stock: 5 },
  { sku: 'KB001', name: 'Mechanical Keyboard', price: '4500.00', stock: 50 },
  { sku: 'MOUSE001', name: 'Ergonomic Mouse', price: '1500.00', stock: 100 },
  { sku: 'MONITOR001', name: '27-inch Monitor', price: '32000.00', stock: 20 },
  { sku: 'HEADSET001', name: 'Noise-Cancelling Headset', price: '8500.00', stock: 30 },
  { sku: 'WEBCAM001', name: 'HD Webcam', price: '3200.00', stock: 0 },
  { sku: 'CHAIR001', name: 'Ergonomic Office Chair', price: '22000.00', stock: 15 },
]

export default function CatalogPage() {
  return (
    <div>
      <h1 className="text-2xl font-sans font-semibold mb-2">Product Catalog</h1>
      <p className="text-sm text-gray-400 mb-6">
        Prices and stock levels are always re-verified from this catalog by the policy gate.
        The agent’s proposed prices are never trusted.
      </p>
      <div className="grid gap-3">
        {CATALOG.map(item => (
          <div key={item.sku} className="border border-gray-800 rounded p-4 flex items-center justify-between">
            <div>
              <div className="font-mono text-xs text-gray-500 mb-1">{item.sku}</div>
              <div className="font-sans text-sm text-gray-100">{item.name}</div>
            </div>
            <div className="text-right flex flex-col items-end gap-1">
              <span className="font-mono text-sm text-accent">INR {item.price}</span>
              {item.stock === 0 ? (
                <span className="text-xs text-red-400 font-sans">Out of stock</span>
              ) : (
                <span className="text-xs text-gray-500 font-sans">{item.stock} in stock</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
