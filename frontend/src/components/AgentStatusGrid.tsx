const ALL_AGENTS = [
  'orchestrator',
  'data_ingestion',
  'pnl_analyzer',
  'forecasting',
  'anomaly_detection',
  'reconciliation',
  'report_generator',
  'notification',
  'audit',
  'dashboard',
] as const

type AgentName = (typeof ALL_AGENTS)[number]
type AgentStatus = 'idle' | 'running' | 'done' | 'error'

interface Props {
  completedAgents: string[]
  errors: { agent: string; error: string }[]
  activeAgent?: string
}

const LABEL: Record<AgentName, string> = {
  orchestrator: 'Orchestrator',
  data_ingestion: 'Data Ingestion',
  pnl_analyzer: 'P&L Analyzer',
  forecasting: 'Forecasting',
  anomaly_detection: 'Anomaly Detection',
  reconciliation: 'Reconciliation',
  report_generator: 'Report Generator',
  notification: 'Notification',
  audit: 'Audit',
  dashboard: 'Dashboard',
}

const STATUS_STYLE: Record<AgentStatus, string> = {
  idle: 'border-slate-700 text-slate-500',
  running: 'border-brand-500 text-brand-400 animate-pulse',
  done: 'border-green-600 text-green-400',
  error: 'border-red-600 text-red-400',
}

const STATUS_DOT: Record<AgentStatus, string> = {
  idle: 'bg-slate-600',
  running: 'bg-brand-500',
  done: 'bg-green-500',
  error: 'bg-red-500',
}

export default function AgentStatusGrid({ completedAgents, errors, activeAgent }: Props) {
  const errorSet = new Set(errors.map((e) => e.agent))

  function getStatus(agent: AgentName): AgentStatus {
    if (errorSet.has(agent)) return 'error'
    if (completedAgents.includes(agent)) return 'done'
    if (agent === activeAgent) return 'running'
    return 'idle'
  }

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl p-4">
      <p className="text-sm font-semibold text-slate-300 mb-3">Agent Status</p>
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
        {ALL_AGENTS.map((agent) => {
          const s = getStatus(agent)
          return (
            <div
              key={agent}
              className={`border rounded-lg p-2 flex flex-col gap-1 ${STATUS_STYLE[s]}`}
            >
              <div className="flex items-center gap-1.5">
                <span className={`w-2 h-2 rounded-full shrink-0 ${STATUS_DOT[s]}`} />
                <span className="text-[11px] font-medium truncate">{LABEL[agent]}</span>
              </div>
              <span className="text-[10px] uppercase tracking-wide opacity-60">{s}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
