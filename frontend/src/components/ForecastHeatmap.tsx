import { useState } from 'react'
import { Forecast } from '../api/client'

const RISK: Record<string, { label: string; color: string; bg: string; border: string }> = {
  critical_understock: { label: 'Critical Low',  color: '#f0415e', bg: 'rgba(240,65,94,0.1)',  border: 'rgba(240,65,94,0.3)' },
  understock:          { label: 'Low Stock',      color: '#f0a430', bg: 'rgba(240,164,48,0.1)', border: 'rgba(240,164,48,0.25)' },
  normal:              { label: 'Normal',          color: '#00d4a0', bg: 'rgba(0,212,160,0.08)', border: 'rgba(0,212,160,0.2)' },
  overstock:           { label: 'Overstock',       color: '#4d8cff', bg: 'rgba(77,140,255,0.1)', border: 'rgba(77,140,255,0.25)' },
  critical_overstock:  { label: 'Critical Over',  color: '#8b5cf6', bg: 'rgba(139,92,246,0.1)', border: 'rgba(139,92,246,0.3)' },
}

interface Props {
  forecasts: Forecast[]
  onSelect: (f: Forecast) => void
}

export default function ForecastHeatmap({ forecasts, onSelect }: Props) {
  const [selectedKey, setSelectedKey] = useState<string | null>(null)

  if (forecasts.length === 0) return (
    <div className="card p-8 text-center text-cosmos-300 text-sm">
      No forecast data. Use the Generate Forecasts button to run analysis.
    </div>
  )

  const order = ['critical_understock','understock','critical_overstock','overstock','normal']
  const sorted = [...forecasts].sort((a,b) => order.indexOf(a.risk_level) - order.indexOf(b.risk_level))

  return (
    <div className="card p-5">
      <div className="flex items-start justify-between mb-4">
        <h3 className="text-sm font-semibold text-cosmos-50">Inventory Risk</h3>
        <div className="flex flex-wrap gap-x-4 gap-y-1">
          {Object.entries(RISK).map(([k, v]) => (
            <div key={k} className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-sm" style={{ background: v.color }} />
              <span className="text-xs text-cosmos-300">{v.label}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="grid gap-2 max-h-72 overflow-y-auto" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))' }}>
        {sorted.map(f => {
          const key = `${f.product_id}-${f.market}`
          const r = RISK[f.risk_level] ?? RISK.normal
          const selected = selectedKey === key
          return (
            <button
              key={key}
              onClick={() => { setSelectedKey(key); onSelect(f) }}
              className="text-left p-3 rounded-lg border transition-all duration-150 hover:scale-[1.02]"
              style={{
                background: r.bg,
                borderColor: selected ? r.color : r.border,
                outline: selected ? `1px solid ${r.color}` : 'none',
                outlineOffset: 1,
              }}
            >
              <p className="text-xs font-medium mb-1" style={{ color: r.color }}>{r.label}</p>
              <p className="text-sm font-medium text-cosmos-50 leading-snug truncate">{f.product_name}</p>
              <p className="text-xs text-cosmos-300 mt-0.5">{f.market} · {f.current_stock.toLocaleString()} units</p>
              {f.signal_count > 0 && (
                <p className="text-xs text-cosmos-400 mt-1">{f.signal_count} signal{f.signal_count !== 1 ? 's' : ''}</p>
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}
