import { useEffect, useState } from 'react'
import { type WSMessage } from '../hooks/useWebSocket'

interface Props {
  lastMessage: WSMessage | null
}

interface LogEntry {
  id: number
  ts: string
  type: string
  agent?: string
  text: string
}

let _id = 0

export default function AgentActivityFeed({ lastMessage }: Props) {
  const [logs, setLogs] = useState<LogEntry[]>([])

  useEffect(() => {
    if (!lastMessage) return

    const entry: LogEntry = {
      id: _id++,
      ts: new Date().toLocaleTimeString(),
      type: lastMessage.type,
      agent: lastMessage.agent,
      text: buildText(lastMessage),
    }

    setLogs((prev) => [entry, ...prev].slice(0, 100))
  }, [lastMessage])

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl p-4 h-80 overflow-y-auto font-mono text-xs">
      <p className="text-slate-500 mb-2 font-sans text-sm font-semibold">Live Activity</p>
      {logs.length === 0 && (
        <p className="text-slate-600">Waiting for pipeline events…</p>
      )}
      {logs.map((l) => (
        <div key={l.id} className="flex gap-2 py-0.5">
          <span className="text-slate-500 shrink-0">{l.ts}</span>
          <span className={typeColor(l.type)}>[{l.type}]</span>
          {l.agent && <span className="text-brand-500">{l.agent}</span>}
          <span className="text-slate-300 truncate">{l.text}</span>
        </div>
      ))}
    </div>
  )
}

function typeColor(type: string) {
  if (type === 'agent_error' || type === 'pipeline_failed') return 'text-red-400'
  if (type === 'agent_done' || type === 'pipeline_complete') return 'text-green-400'
  if (type === 'agent_started') return 'text-yellow-400'
  return 'text-slate-400'
}

function buildText(msg: WSMessage): string {
  if (msg.type === 'pipeline_complete') {
    const m = msg.metrics
    return m
      ? `Revenue $${m.revenue?.toLocaleString()} | Net Profit $${m.net_profit?.toLocaleString()} | Anomalies: ${m.anomalies_flagged}`
      : 'Pipeline complete'
  }
  if (msg.type === 'agent_started') return `${msg.agent} starting…`
  if (msg.type === 'agent_done') return `${msg.agent} done`
  if (msg.type === 'agent_error') return `${msg.agent} failed`
  return JSON.stringify(msg).slice(0, 80)
}
