import { useState, useEffect } from 'react'
import { dashboardApi, DashboardSummary } from '../api/client'

export default function ExecutiveSummary() {
  const [data, setData] = useState<DashboardSummary | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => { load() }, [])

  async function load() {
    setLoading(true)
    try { const { data } = await dashboardApi.summary(); setData(data) }
    catch { /* ignore */ }
    finally { setLoading(false) }
  }

  const metrics = data ? [
    { label: 'Conversations',   value: data.metrics.total_conversations,            color: 'text-nova-blue' },
    { label: 'Demand Signals',  value: data.metrics.total_signals,                  color: 'text-nova-violet' },
    { label: 'Neg. Sentiment',  value: `${data.metrics.negative_sentiment_pct}%`,   color: 'text-nova-red' },
    { label: 'Critical Issues', value: data.metrics.critical_issues,                color: 'text-nova-amber' },
    { label: 'Pos. Signals',    value: data.metrics.positive_signals,               color: 'text-nova-green' },
    { label: 'Peer Benchmark',  value: `${data.metrics.peer_benchmark_pct}%`,       color: 'text-cosmos-200' },
  ] : []

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-cosmos-50">Executive Summary</h3>
        <button onClick={load} disabled={loading} className="btn-ghost">
          {loading ? 'Generating...' : 'Refresh'}
        </button>
      </div>

      {loading ? (
        <div className="space-y-2 animate-pulse">
          <div className="h-3 bg-cosmos-600 rounded w-full" />
          <div className="h-3 bg-cosmos-600 rounded w-5/6" />
          <div className="h-3 bg-cosmos-600 rounded w-4/6" />
        </div>
      ) : data ? (
        <div className="space-y-4">
          <p className="text-sm text-cosmos-100 leading-relaxed bg-cosmos-700/40 border border-white/8 rounded-lg p-4">
            {data.summary}
          </p>
          <div className="grid grid-cols-3 gap-2">
            {metrics.map(m => (
              <div key={m.label} className="bg-cosmos-800/60 border border-white/6 rounded-lg p-3 text-center">
                <p className={`text-lg font-semibold tabular-nums ${m.color}`}>{m.value}</p>
                <p className="text-xs text-cosmos-300 mt-0.5 leading-tight">{m.label}</p>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <p className="text-xs text-cosmos-300 text-center py-4">Click Refresh to generate an AI summary.</p>
      )}
    </div>
  )
}
