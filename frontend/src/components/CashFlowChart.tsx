import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'

interface DataPoint {
  label: string
  projected: number
  actual?: number
}

interface Props {
  data: DataPoint[]
}

export default function CashFlowChart({ data }: Props) {
  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl p-4">
      <p className="text-sm font-semibold text-slate-300 mb-4">Cash Flow Forecast</p>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data} margin={{ top: 4, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="label" tick={{ fill: '#64748b', fontSize: 11 }} />
          <YAxis tick={{ fill: '#64748b', fontSize: 11 }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
          <Tooltip
            contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 8 }}
            labelStyle={{ color: '#94a3b8' }}
            formatter={(value: number) => [`$${value.toLocaleString()}`, '']}
          />
          <ReferenceLine y={0} stroke="#475569" />
          <Bar dataKey="actual" fill="#0ea5e9" radius={[4, 4, 0, 0]} name="Actual" />
          <Bar dataKey="projected" fill="#7c3aed" radius={[4, 4, 0, 0]} name="Projected" opacity={0.7} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
