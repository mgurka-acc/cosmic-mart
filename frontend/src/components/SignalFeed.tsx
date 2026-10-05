import { useState, useEffect } from 'react'
import { signalsApi, Signal } from '../api/client'

const SIGNAL_TYPE_LABELS: Record<string, string> = {
  demand_expressed:       'Demand',
  availability_complaint: 'Availability',
  return_intent:          'Return Intent',
  price_concern:          'Price',
  competitor_mention:     'Competitor',
}

const SENTIMENT_STYLES: Record<string, string> = {
  positive: 'text-nova-green',
  neutral:  'text-cosmos-200',
  negative: 'text-nova-red',
}

interface Props {
  market?: string
  refreshTrigger?: number
}

export default function SignalFeed({ market, refreshTrigger }: Props) {
  const [signals, setSignals] = useState<Signal[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => { loadSignals() }, [market, refreshTrigger])

  async function loadSignals() {
    setLoading(true)
    try {
      const { data } = await signalsApi.list(market)
      setSignals(data.signals.slice(0, 25))
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }

  return (
    <div className="card p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-cosmos-50">Signal Feed</h3>
        <button onClick={loadSignals} className="btn-ghost">Refresh</button>
      </div>

      {loading ? (
        <p className="text-xs text-cosmos-300 py-4 text-center">Loading...</p>
      ) : signals.length === 0 ? (
        <p className="text-xs text-cosmos-300 py-4 text-center">
          No signals yet. Complete a conversation in the Support view to generate signals.
        </p>
      ) : (
        <div className="space-y-2 max-h-80 overflow-y-auto -mr-1 pr-1">
          {signals.map(s => (
            <div key={s.id} className="bg-cosmos-800/60 border border-white/6 rounded-lg p-3 hover:border-white/12 transition-colors">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-medium text-cosmos-100 truncate">{s.product_name}</span>
                    <span className="label">{SIGNAL_TYPE_LABELS[s.signal_type] ?? s.signal_type}</span>
                    <span className="label">{s.market}</span>
                  </div>
                  {s.raw_quote && (
                    <p className="text-xs text-cosmos-300 mt-1.5 italic line-clamp-2">"{s.raw_quote}"</p>
                  )}
                </div>
                <div className="shrink-0 text-right space-y-0.5">
                  <p className={`text-xs font-medium ${SENTIMENT_STYLES[s.sentiment]}`}>{s.sentiment}</p>
                  <p className="text-xs text-cosmos-400">urgency {s.urgency}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
