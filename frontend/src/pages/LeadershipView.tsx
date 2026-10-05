import { useState, useEffect } from 'react'
import { forecastApi, dashboardApi, Forecast } from '../api/client'
import ForecastHeatmap    from '../components/ForecastHeatmap'
import RecommendationCard from '../components/RecommendationCard'
import SentimentGauge     from '../components/SentimentGauge'
import ExecutiveSummary   from '../components/ExecutiveSummary'
import SignalFeed         from '../components/SignalFeed'

export default function LeadershipView() {
  const [forecasts, setForecasts]     = useState<Forecast[]>([])
  const [selected, setSelected]       = useState<Forecast | null>(null)
  const [sentiment, setSentiment]     = useState<{ breakdown: Record<string,number> } | null>(null)
  const [loading, setLoading]         = useState(true)
  const [generating, setGenerating]   = useState(false)
  const [lastUpdated, setLastUpdated] = useState<string | null>(null)

  useEffect(() => { loadData() }, [])

  async function loadData() {
    setLoading(true)
    try {
      const [fRes, sRes] = await Promise.all([forecastApi.list(), dashboardApi.sentiment()])
      setForecasts(fRes.data.forecasts)
      setSentiment(sRes.data)
      setLastUpdated(new Date().toLocaleTimeString())
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }

  async function runForecast() {
    setGenerating(true)
    try { await forecastApi.generate(); await loadData() }
    catch { /* ignore */ }
    finally { setGenerating(false) }
  }

  const critical = forecasts.filter(f => f.risk_level.startsWith('critical')).length

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-lg font-semibold text-cosmos-50 tracking-tight">Operations Intelligence</h1>
          <p className="text-sm text-cosmos-300 mt-0.5">
            AI-extracted demand signals from customer conversations
            {lastUpdated && <span className="ml-2 text-cosmos-400">· Updated {lastUpdated}</span>}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {critical > 0 && (
            <span className="text-xs font-medium px-2.5 py-1 rounded-md bg-nova-red/10 text-nova-red border border-nova-red/20">
              {critical} critical issue{critical !== 1 ? 's' : ''}
            </span>
          )}
          <button onClick={runForecast} disabled={generating} className="btn-primary">
            {generating ? 'Analyzing...' : 'Generate Forecasts'}
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-center text-cosmos-300 py-24 text-sm">Loading data...</div>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div>
              {sentiment && (
                <SentimentGauge
                  negative={sentiment.breakdown?.negative ?? 0}
                  neutral={sentiment.breakdown?.neutral ?? 0}
                  positive={sentiment.breakdown?.positive ?? 0}
                />
              )}
            </div>
            <div className="lg:col-span-2">
              <ExecutiveSummary />
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2">
              <ForecastHeatmap forecasts={forecasts} onSelect={setSelected} />
            </div>
            <div>
              <RecommendationCard forecast={selected} />
            </div>
          </div>

          <SignalFeed />
        </div>
      )}
    </div>
  )
}
