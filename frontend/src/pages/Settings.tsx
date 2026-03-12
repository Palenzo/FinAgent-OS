export default function Settings() {
  return (
    <div className="space-y-6 max-w-xl">
      <h1 className="text-2xl font-bold">Settings</h1>

      <section className="bg-slate-900 border border-slate-700 rounded-xl p-6 space-y-4">
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide">Environment</h2>
        <div className="space-y-2 text-sm">
          <Row label="API URL" value={import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'} />
          <Row label="WebSocket URL" value={import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'} />
          <Row label="Environment" value={import.meta.env.MODE} />
        </div>
      </section>

      <section className="bg-slate-900 border border-slate-700 rounded-xl p-6 space-y-4">
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide">Pipeline Configuration</h2>
        <p className="text-slate-500 text-sm">
          All pipeline settings are managed via <code className="text-brand-400">.env</code> on the backend.
          Connect to the API and update environment variables to change Claude models, alert thresholds, and
          scheduled run times.
        </p>
      </section>

      <section className="bg-slate-900 border border-slate-700 rounded-xl p-6">
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-3">Agent Model Assignments</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-slate-500 text-xs border-b border-slate-800">
              <th className="text-left pb-2">Agent</th>
              <th className="text-left pb-2">Model</th>
            </tr>
          </thead>
          <tbody className="text-slate-300">
            {[
              ['Orchestrator', 'claude-sonnet-4-6'],
              ['P&L Analyzer', 'claude-sonnet-4-6'],
              ['Forecasting', 'claude-sonnet-4-6'],
              ['Anomaly Detection', 'claude-sonnet-4-6'],
              ['Reconciliation', 'claude-sonnet-4-6'],
              ['Report Generator', 'claude-opus-4-6'],
              ['Notification', '(no LLM)'],
              ['Audit', '(no LLM)'],
              ['Dashboard', '(no LLM)'],
            ].map(([agent, model]) => (
              <tr key={agent} className="border-b border-slate-800/50">
                <td className="py-2">{agent}</td>
                <td className="py-2 text-brand-400 font-mono text-xs">{model}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-slate-500">{label}</span>
      <span className="text-slate-200 font-mono text-xs">{value}</span>
    </div>
  )
}
