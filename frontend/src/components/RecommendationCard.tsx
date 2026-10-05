import { Forecast } from '../api/client'

const RISK: Record<string, { label: string; color: string }> = {
  critical_understock: { label: 'Critical Understock', color: '#f0415e' },
  understock:          { label: 'Low Stock',           color: '#f0a430' },
  normal:              { label: 'Normal',               color: '#00d4a0' },
  overstock:           { label: 'Overstock',            color: '#4d8cff' },
  critical_overstock:  { label: 'Critical Overstock',  color: '#8b5cf6' },
}

interface Props { forecast: Forecast | null }

export default function RecommendationCard({ forecast }: Props) {
  if (!forecast) return (
    <div className="card p-6 text-center text-cosmos-300 text-sm">
      Select a product from the risk grid to view recommendations.
    </div>
  )

  const r = RISK[forecast.risk_level] ?? RISK.normal

  return (
    <div className="card p-5 space-y-4" style={{ borderColor: `${r.color}28` }}>
      <div>
        <p className="label" style={{ color: r.color }}>{r.label}</p>
        <h3 className="text-base font-semibold text-cosmos-50 mt-1 leading-snug">{forecast.product_name}</h3>
        <p className="text-xs text-cosmos-300 mt-0.5">{forecast.market} · {forecast.current_stock.toLocaleString()} units · {forecast.signal_count} signal{forecast.signal_count !== 1 ? 's' : ''}</p>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex-1 bg-cosmos-700 rounded-full h-1.5 overflow-hidden">
          <div
            className="h-full rounded-full transition-all"
            style={{ width: `${Math.round(forecast.risk_score * 100)}%`, background: r.color }}
          />
        </div>
        <span className="text-xs font-semibold tabular-nums" style={{ color: r.color }}>
          {Math.round(forecast.risk_score * 100)}
        </span>
      </div>

      <div className="bg-cosmos-700/50 border border-white/8 rounded-lg p-3.5">
        <p className="label mb-1.5">Recommendation</p>
        <p className="text-sm text-cosmos-50 leading-relaxed">{forecast.recommendation}</p>
      </div>

      <div>
        <p className="label mb-1.5">AI Analysis</p>
        <p className="text-xs text-cosmos-200 leading-relaxed">{forecast.ai_reasoning}</p>
      </div>
    </div>
  )
}
