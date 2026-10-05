import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'

interface Props {
  negative: number
  neutral: number
  positive: number
  peerBenchmark?: number
}

export default function SentimentGauge({ negative, neutral, positive, peerBenchmark = 19.5 }: Props) {
  const total = negative + neutral + positive
  const negPct = total > 0 ? Math.round(negative / total * 100) : 0

  const data = [
    { name: 'Negative', value: negative, color: '#f0415e' },
    { name: 'Neutral',  value: neutral,  color: '#3a3a6a' },
    { name: 'Positive', value: positive, color: '#00d4a0' },
  ]

  return (
    <div className="card p-5">
      <h3 className="text-sm font-semibold text-cosmos-50 mb-4">Customer Sentiment</h3>
      <div className="flex items-center gap-5">
        <div className="relative w-28 h-28 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data} cx="50%" cy="50%"
                innerRadius={34} outerRadius={52}
                dataKey="value" stroke="none" startAngle={90} endAngle={-270}
              >
                {data.map((d, i) => <Cell key={i} fill={d.color} />)}
              </Pie>
              <Tooltip
                contentStyle={{ background: '#0e0e2c', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 12 }}
                labelStyle={{ color: '#eeeeff' }}
                itemStyle={{ color: '#8888b8' }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-xl font-semibold text-nova-red leading-none">{negPct}%</span>
            <span className="text-xs text-cosmos-300 mt-0.5">neg</span>
          </div>
        </div>

        <div className="flex-1 space-y-2.5">
          {data.map(d => (
            <div key={d.name} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-sm shrink-0" style={{ background: d.color }} />
                <span className="text-xs text-cosmos-200">{d.name}</span>
              </div>
              <span className="text-xs font-medium text-cosmos-100">{d.value}</span>
            </div>
          ))}
          <div className="pt-2 border-t border-white/8">
            <div className="flex items-center justify-between">
              <span className="text-xs text-cosmos-300">Peer benchmark</span>
              <span className="text-xs font-medium text-nova-green">{peerBenchmark}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
