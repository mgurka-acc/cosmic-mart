import { useState } from 'react'
import ChatWidget from '../components/ChatWidget'

const MARKETS = [
  { id: 'US', label: 'United States', currency: 'USD' },
  { id: 'UK', label: 'United Kingdom', currency: 'GBP' },
  { id: 'DE', label: 'Germany',        currency: 'EUR' },
  { id: 'FR', label: 'France',         currency: 'EUR' },
  { id: 'JP', label: 'Japan',          currency: 'JPY' },
  { id: 'AU', label: 'Australia',      currency: 'AUD' },
  { id: 'CA', label: 'Canada',         currency: 'CAD' },
  { id: 'BR', label: 'Brazil',         currency: 'BRL' },
  { id: 'IN', label: 'India',          currency: 'INR' },
  { id: 'SG', label: 'Singapore',      currency: 'SGD' },
]

export default function CustomerView() {
  const [market, setMarket] = useState('US')

  return (
    <div className="min-h-[calc(100vh-3.5rem)] flex flex-col items-center justify-start py-10 px-4">
      <div className="w-full max-w-xl mb-6 text-center">
        <h1 className="text-xl font-semibold text-cosmos-50 tracking-tight">Support Center</h1>
        <p className="text-sm text-cosmos-200 mt-1">How can we help you today?</p>
      </div>

      <div className="w-full max-w-xl mb-4 flex items-center justify-end gap-2">
        <span className="text-xs text-cosmos-300">Region</span>
        <select
          value={market}
          onChange={e => setMarket(e.target.value)}
          className="field w-auto text-sm py-1.5 px-3 pr-8 appearance-none cursor-pointer"
          style={{ backgroundImage: 'none' }}
        >
          {MARKETS.map(m => (
            <option key={m.id} value={m.id}>{m.label}</option>
          ))}
        </select>
      </div>

      <div className="w-full max-w-xl" style={{ height: 'calc(100vh - 260px)', minHeight: 420 }}>
        <ChatWidget market={market} />
      </div>
    </div>
  )
}
