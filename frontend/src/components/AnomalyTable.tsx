import { type AnomalyItem } from '../hooks/useWebSocket'

interface Props {
  anomalies: AnomalyItem[]
}

const SEVERITY_STYLE: Record<string, string> = {
  critical: 'bg-red-900/60 text-red-300 border border-red-700',
  high: 'bg-orange-900/50 text-orange-300 border border-orange-700',
  medium: 'bg-yellow-900/40 text-yellow-300 border border-yellow-700',
  low: 'bg-slate-700 text-slate-300',
}

export default function AnomalyTable({ anomalies }: Props) {
  if (anomalies.length === 0) {
    return (
      <div className="bg-slate-900 border border-slate-700 rounded-xl p-4">
        <p className="text-sm font-semibold text-slate-300 mb-2">Anomaly Report</p>
        <p className="text-slate-500 text-sm">No anomalies detected in this run.</p>
      </div>
    )
  }

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl p-4">
      <p className="text-sm font-semibold text-slate-300 mb-3">
        Anomaly Report{' '}
        <span className="text-red-400 text-xs ml-2">{anomalies.length} flagged</span>
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-slate-500 border-b border-slate-800">
              <th className="text-left pb-2 pr-3">Date</th>
              <th className="text-left pb-2 pr-3">Description</th>
              <th className="text-right pb-2 pr-3">Amount</th>
              <th className="text-left pb-2 pr-3">Severity</th>
              <th className="text-left pb-2">Reason</th>
            </tr>
          </thead>
          <tbody>
            {anomalies.map((a, i) => (
              <tr key={i} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                <td className="py-2 pr-3 text-slate-400 whitespace-nowrap">
                  {a.transaction_date?.slice(0, 10)}
                </td>
                <td className="py-2 pr-3 text-slate-300 max-w-[180px] truncate">
                  {a.description}
                </td>
                <td className="py-2 pr-3 text-right text-slate-200 whitespace-nowrap">
                  ${a.amount?.toLocaleString()}
                </td>
                <td className="py-2 pr-3">
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                      SEVERITY_STYLE[a.severity] ?? SEVERITY_STYLE.low
                    }`}
                  >
                    {a.severity}
                  </span>
                </td>
                <td className="py-2 text-slate-400 max-w-[220px] truncate" title={a.reason}>
                  {a.reason}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
