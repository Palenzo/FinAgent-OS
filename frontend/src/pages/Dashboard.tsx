import { useState, useRef } from 'react'
import { useWebSocket, type WSMessage } from '../hooks/useWebSocket'
import AgentActivityFeed from '../components/AgentActivityFeed'
import AgentStatusGrid from '../components/AgentStatusGrid'
import PnLChart from '../components/PnLChart'
import CashFlowChart from '../components/CashFlowChart'
import AnomalyTable from '../components/AnomalyTable'

const API = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

interface Metrics {
  revenue?: number
  net_profit?: number
  gross_margin_pct?: number
  health_score?: number
  anomalies_flagged?: number
  critical_anomalies?: number
  match_rate_pct?: number
  forecast_30d?: number
  forecast_90d?: number
}

export default function Dashboard() {
  const { status: wsStatus, lastMessage } = useWebSocket()
  const [metrics, setMetrics] = useState<Metrics>({})
  const [completedAgents, setCompletedAgents] = useState<string[]>([])
  const [errors, setErrors] = useState<{ agent: string; error: string }[]>([])
  const [anomalies, setAnomalies] = useState<WSMessage['anomalies']>([])
  const [uploading, setUploading] = useState(false)
  const [runStatus, setRunStatus] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  // React to WebSocket messages
  useState(() => {
    if (!lastMessage) return
    if (lastMessage.type === 'pipeline_complete') {
      if (lastMessage.metrics) setMetrics(lastMessage.metrics as Metrics)
      if (lastMessage.completed_agents) setCompletedAgents(lastMessage.completed_agents)
      if (lastMessage.errors) setErrors(lastMessage.errors)
      if (lastMessage.anomalies) setAnomalies(lastMessage.anomalies)
      setRunStatus(lastMessage.status ?? null)
    }
  })

  async function handleUpload() {
    const file = fileRef.current?.files?.[0]
    if (!file) return alert('Please select a CSV file first')

    setUploading(true)
    setRunStatus('running')
    const form = new FormData()
    form.append('file', file)
    form.append('file_type', file.name.endsWith('.json') ? 'json' : 'csv')
    form.append('triggered_by', 'manual')

    try {
      const res = await fetch(`${API}/api/v1/run`, { method: 'POST', body: form })
      const data = await res.json()
      setRunStatus(data.status)
      setCompletedAgents(data.completed_agents ?? [])
      setErrors(data.errors ?? [])
    } catch (e) {
      setRunStatus('error')
    } finally {
      setUploading(false)
    }
  }

  // Build chart data from metrics (stub — real app pulls from /reports)
  const pnlData = metrics.revenue
    ? [
        { period: 'Current', revenue: metrics.revenue, expenses: (metrics.revenue ?? 0) - (metrics.net_profit ?? 0), net_profit: metrics.net_profit ?? 0 },
      ]
    : []

  const cashFlowData = [
    { label: '30d', projected: metrics.forecast_30d ?? 0 },
    { label: '90d', projected: metrics.forecast_90d ?? 0 },
  ]

  return (
    <div className="space-y-6">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Financial Operations Dashboard</h1>
          <p className="text-slate-500 text-sm mt-0.5">
            WS: <span className={wsStatus === 'open' ? 'text-green-400' : 'text-red-400'}>{wsStatus}</span>
            {runStatus && <span className="ml-4">Last run: <span className="text-brand-400">{runStatus}</span></span>}
          </p>
        </div>

        {/* Upload trigger */}
        <div className="flex gap-2 items-center">
          <input ref={fileRef} type="file" accept=".csv,.json" className="hidden" />
          <button
            onClick={() => fileRef.current?.click()}
            className="px-3 py-2 text-sm bg-slate-800 border border-slate-700 rounded-lg hover:bg-slate-700"
          >
            Select CSV
          </button>
          <button
            onClick={handleUpload}
            disabled={uploading}
            className="px-4 py-2 text-sm bg-brand-600 rounded-lg hover:bg-brand-500 disabled:opacity-50"
          >
            {uploading ? 'Running…' : '▶ Run Pipeline'}
          </button>
        </div>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard label="Revenue" value={fmt(metrics.revenue)} />
        <KpiCard label="Net Profit" value={fmt(metrics.net_profit)} />
        <KpiCard label="Gross Margin" value={metrics.gross_margin_pct != null ? `${metrics.gross_margin_pct}%` : '—'} />
        <KpiCard label="Health Score" value={metrics.health_score != null ? `${metrics.health_score}/100` : '—'} />
        <KpiCard label="Anomalies" value={String(metrics.anomalies_flagged ?? '—')} warn={!!metrics.critical_anomalies} />
        <KpiCard label="Critical" value={String(metrics.critical_anomalies ?? '—')} warn={!!metrics.critical_anomalies} />
        <KpiCard label="Recon Match" value={metrics.match_rate_pct != null ? `${metrics.match_rate_pct}%` : '—'} />
        <KpiCard label="30d Forecast" value={fmt(metrics.forecast_30d)} />
      </div>

      {/* Agent grid */}
      <AgentStatusGrid completedAgents={completedAgents} errors={errors} />

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <PnLChart data={pnlData} />
        <CashFlowChart data={cashFlowData} />
      </div>

      {/* Anomaly table */}
      <AnomalyTable anomalies={anomalies ?? []} />

      {/* Live feed */}
      <AgentActivityFeed lastMessage={lastMessage} />
    </div>
  )
}

function fmt(n?: number | null) {
  if (n == null) return '—'
  return `$${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}`
}

function KpiCard({ label, value, warn = false }: { label: string; value: string; warn?: boolean }) {
  return (
    <div className={`bg-slate-900 border rounded-xl p-4 ${warn ? 'border-red-700' : 'border-slate-700'}`}>
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <p className={`text-2xl font-bold ${warn ? 'text-red-400' : 'text-white'}`}>{value}</p>
    </div>
  )
}
