import type { Metadata } from 'next'
import Link from 'next/link'
import './globals.css'

export const metadata: Metadata = {
  title: 'Covenant',
  description: 'Agentic commerce with cryptographic mandate chain',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-950 text-gray-100 font-sans">
        <header className="border-b border-gray-800 px-6 py-4 flex items-center gap-6">
          <Link href="/" className="font-mono text-lg text-accent font-medium hover:text-accent-hover">
            Covenant
          </Link>
          <nav className="flex gap-4 text-sm text-gray-400">
            <Link href="/" className="hover:text-gray-100">Request</Link>
            <Link href="/mandates" className="hover:text-gray-100">Mandates</Link>
            <Link href="/audit" className="hover:text-gray-100">Audit</Link>
            <Link href="/catalog" className="hover:text-gray-100">Catalog</Link>
          </nav>
        </header>
        <main className="px-6 py-8 max-w-5xl mx-auto">{children}</main>
      </body>
    </html>
  )
}
