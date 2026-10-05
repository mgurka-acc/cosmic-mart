import axios from 'axios'

// In dev, VITE_API_URL is unset and Vite proxy routes /api → localhost:8000.
// In production (Render static site), set VITE_API_URL to your backend URL.
export const API_BASE = import.meta.env.VITE_API_URL ?? ''

// SSE streaming must bypass the Vite dev proxy (which buffers the stream).
// In dev this is localhost:8000 directly; in prod it equals API_BASE.
export const STREAM_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const api = axios.create({
  baseURL: `${API_BASE}/api`,
  headers: { 'Content-Type': 'application/json' }
})

export interface ConversationStart {
  conversation_id: number
  session_id: string
  market: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

export interface Signal {
  id: number
  conversation_id: number
  extracted_at: string
  product_id: string | null
  product_name: string
  signal_type: string
  sentiment: string
  complaint_category: string | null
  return_reason: string | null
  market: string
  urgency: number
  raw_quote: string | null
  confidence: number
}

export interface Forecast {
  id: number
  product_id: string
  product_name: string
  market: string
  risk_level: string
  risk_score: number
  signal_count: number
  current_stock: number
  recommendation: string
  ai_reasoning: string
}

export interface DashboardSummary {
  summary: string
  metrics: {
    total_conversations: number
    total_signals: number
    negative_sentiment_pct: number
    positive_signals: number
    critical_issues: number
    peer_benchmark_pct: number
  }
}

export const chatApi = {
  start: (market: string) =>
    api.post<ConversationStart>('/chat/start', { market }),
  history: (id: number) =>
    api.get<{ messages: ChatMessage[]; status: string }>(`/chat/${id}/history`)
}

export const signalsApi = {
  list: (market?: string) =>
    api.get<{ signals: Signal[]; count: number }>('/signals', { params: market ? { market } : {} }),
  extract: (conversationId: number) =>
    api.post(`/signals/extract/${conversationId}`)
}

export const forecastApi = {
  list: (market?: string) =>
    api.get<{ forecasts: Forecast[] }>('/forecast', { params: market ? { market } : {} }),
  generate: (market?: string) =>
    api.post<{ generated: number }>('/forecast/generate', {}, { params: market ? { market } : {} })
}

export const dashboardApi = {
  summary: () => api.get<DashboardSummary>('/dashboard/summary'),
  sentiment: () => api.get('/dashboard/sentiment'),
  heatmap: () => api.get<{ heatmap: Forecast[] }>('/dashboard/heatmap')
}

export default api
