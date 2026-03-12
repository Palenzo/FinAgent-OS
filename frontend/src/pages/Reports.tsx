import { useEffect, useState } from 'react'

const API = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

interface ReportSummary {
  id: string
  run_id: string
  period_start: string | null
  period_end: string | null
  created_at: string
}

interface ReportDetail {
  id: string
  markdown_report: string
  executive_summary: string
  pnl_data: Record<string, unknown>
  anomalies: unknown[]
  forecast_data: Record<string, unknown>
  created_at: string
}

export default function Reports() {
  const [reports, setReports] = useState<ReportSummary[]>([])
  const [selected, setSelected] = useState<ReportDetail | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetch(`${API}/api/v1/reports`)
      .then((r) => r.json())
      .then(setReports)
      .catch(() => {})
  }, [])

  async function openReport(id: string) {
    setLoading(true)
    try {
      const res = await fetch(`${API}/api/v1/reports/${id}`)
      const data = await res.json()
      setSelected(data)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Financial Reports</h1>

      {reports.length === 0 && (
        <p className="text-slate-500">No reports yet. Run the pipeline to generate one.</p>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {reports.map((r) => (
          <button
            key={r.id}
            onClick={() => openReport(r.id)}
            className="bg-slate-900 border border-slate-700 rounded-xl p-4 text-left hover:border-brand-500 transition-colors"
          >
            <p className="text-xs text-slate-500 mb-1">{new Date(r.created_at).toLocaleString()}</p>
            <p className="text-sm font-medium text-slate-200 truncate">Run {r.run_id.slice(0, 8)}</p>
          </button>
        ))}
      </div>

      {loading && <p className="text-slate-500">Loading report…</p>}

      {selected && !loading && (
        <div className="bg-slate-900 border border-slate-700 rounded-xl p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold">Report Detail</h2>
            <button onClick={() => setSelected(null)} className="text-slate-500 hover:text-slate-200">✕</button>
          </div>
          <pre className="text-slate-300 text-xs whitespace-pre-wrap font-mono max-h-[60vh] overflow-y-auto">
            {selected.markdown_report || selected.executive_summary || 'No content'}
          </pre>
        </div>
      )}
    </div>
  )
}
