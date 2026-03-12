import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'

interface DataPoint {
  period: string
  revenue: number
  expenses: number
  net_profit: number
}

interface Props {
  data: DataPoint[]
}

export default function PnLChart({ data }: Props) {
  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl p-4">
      <p className="text-sm font-semibold text-slate-300 mb-4">P&amp;L Overview</p>
      <ResponsiveContainer width="100%" height={260}>
        <AreaChart data={data} margin={{ top: 4, right: 12, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="expGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#f43f5e" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="period" tick={{ fill: '#64748b', fontSize: 11 }} />
          <YAxis tick={{ fill: '#64748b', fontSize: 11 }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
          <Tooltip
            contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 8 }}
            labelStyle={{ color: '#94a3b8' }}
            formatter={(value: number) => [`$${value.toLocaleString()}`, '']}
          />
          <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
          <Area type="monotone" dataKey="revenue" stroke="#0ea5e9" fill="url(#revGrad)" name="Revenue" />
          <Area type="monotone" dataKey="expenses" stroke="#f43f5e" fill="url(#expGrad)" name="Expenses" />
          <Area type="monotone" dataKey="net_profit" stroke="#22c55e" fill="none" strokeDasharray="4 2" name="Net Profit" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
