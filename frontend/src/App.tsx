import { useState } from 'react'
import Dashboard from './pages/Dashboard'
import Reports from './pages/Reports'
import Settings from './pages/Settings'

type Page = 'dashboard' | 'reports' | 'settings'

export default function App() {
  const [page, setPage] = useState<Page>('dashboard')

  return (
    <div className="min-h-screen flex flex-col">
      {/* Nav */}
      <header className="border-b border-slate-800 px-6 py-3 flex items-center gap-8">
        <span className="text-xl font-bold tracking-tight text-brand-500">
          FinAgent OS
        </span>
        <nav className="flex gap-4 text-sm">
          {(['dashboard', 'reports', 'settings'] as Page[]).map((p) => (
            <button
              key={p}
              onClick={() => setPage(p)}
              className={`capitalize px-3 py-1.5 rounded-md transition-colors ${
                page === p
                  ? 'bg-brand-600 text-white'
                  : 'text-slate-400 hover:text-slate-100'
              }`}
            >
              {p}
            </button>
          ))}
        </nav>
      </header>

      {/* Page */}
      <main className="flex-1 p-6">
        {page === 'dashboard' && <Dashboard />}
        {page === 'reports' && <Reports />}
        {page === 'settings' && <Settings />}
      </main>
    </div>
  )
}
