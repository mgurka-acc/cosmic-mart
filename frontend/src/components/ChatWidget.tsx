import { useState, useRef, useEffect } from 'react'
import { chatApi, STREAM_BASE } from '../api/client'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  streaming?: boolean
}

interface Props {
  market: string
}

export default function ChatWidget({ market }: Props) {
  const [messages, setMessages]   = useState<ChatMessage[]>([])
  const [input, setInput]         = useState('')
  const [conversationId, setConversationId] = useState<number | null>(null)
  const [status, setStatus]       = useState<'active' | 'escalated' | 'completed'>('active')
  const [isStreaming, setIsStreaming] = useState(false)
  const [toolActivity, setToolActivity] = useState<string | null>(null)
  const [isStarting, setIsStarting]   = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef  = useRef<HTMLTextAreaElement>(null)
  const prevMarket = useRef(market)

  useEffect(() => {
    startConversation()
  }, [])

  useEffect(() => {
    if (market !== prevMarket.current) {
      prevMarket.current = market
      startConversation()
    }
  }, [market])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, toolActivity])

  async function startConversation() {
    setMessages([])
    setStatus('active')
    setIsStreaming(false)
    setToolActivity(null)
    setIsStarting(true)
    try {
      const { data } = await chatApi.start(market)
      setConversationId(data.conversation_id)
      setMessages([{
        role: 'assistant',
        content: 'Hello. I am Nova, your Cosmic Mart support assistant. I can help with product availability, order tracking, returns, and more. How can I help you?',
      }])
    } catch {
      setMessages([{ role: 'assistant', content: 'Unable to connect. Please try again.' }])
    } finally {
      setIsStarting(false)
    }
  }

  async function sendMessage() {
    if (!input.trim() || !conversationId || isStreaming || status !== 'active') return

    const userMsg = input.trim()
    setInput('')
    setIsStreaming(true)
    setToolActivity(null)

    setMessages(prev => [
      ...prev,
      { role: 'user', content: userMsg },
      { role: 'assistant', content: '', streaming: true },
    ])

    try {
      const response = await fetch(`${STREAM_BASE}/api/chat/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conversation_id: conversationId, message: userMsg }),
      })

      if (!response.body) return
      const reader  = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let assistantText = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const ev = JSON.parse(line.slice(6))
            if (ev.type === 'text') {
              assistantText += ev.content
              setMessages(prev => {
                const copy = [...prev]
                const last = copy[copy.length - 1]
                if (last?.role === 'assistant') copy[copy.length - 1] = { ...last, content: assistantText }
                return copy
              })
            } else if (ev.type === 'tool_call') {
              const labels: Record<string, string> = {
                search_product_catalog: 'Checking product catalog',
                get_order_status:       'Looking up order',
                submit_return_request:  'Processing return request',
                escalate_to_human:      'Escalating to support team',
              }
              setToolActivity(labels[ev.tool] ?? ev.tool)
            } else if (ev.type === 'done') {
              setMessages(prev => {
                const copy = [...prev]
                const last = copy[copy.length - 1]
                if (last?.role === 'assistant') copy[copy.length - 1] = { ...last, streaming: false }
                return copy
              })
              setToolActivity(null)
              if (ev.escalated) setStatus('escalated')
            }
          } catch { /* partial chunk */ }
        }
      }
    } catch {
      setMessages(prev => {
        const copy = [...prev]
        copy[copy.length - 1] = { role: 'assistant', content: 'Something went wrong. Please try again.' }
        return copy
      })
    } finally {
      setIsStreaming(false)
    }

    if (conversationId) {
      try {
        const { data } = await chatApi.history(conversationId)
        if (data.status !== 'active') setStatus(data.status as typeof status)
      } catch { /* ignore */ }
    }

    inputRef.current?.focus()
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
  }

  const canSend = !!input.trim() && !isStreaming && status === 'active' && !isStarting

  const statusConfig = {
    active:    { label: 'Online',    color: 'bg-nova-green' },
    escalated: { label: 'Escalated', color: 'bg-nova-amber' },
    completed: { label: 'Ended',     color: 'bg-cosmos-300' },
  }
  const sc = statusConfig[status]

  return (
    <div className="card flex flex-col h-full overflow-hidden">
      <div className="px-5 py-3.5 border-b border-white/8 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2.5">
          <span className={`w-1.5 h-1.5 rounded-full ${sc.color}`} />
          <span className="text-sm font-medium text-cosmos-50">Nova</span>
          <span className="text-xs text-cosmos-300">Support Assistant</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-cosmos-300">{sc.label}</span>
          <button
            onClick={startConversation}
            disabled={isStarting || isStreaming}
            className="btn-ghost text-xs"
          >
            New chat
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-5 space-y-4">
        {isStarting && (
          <div className="text-center text-cosmos-300 text-sm py-8">Connecting...</div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'assistant' && (
              <div className="flex flex-col gap-1 max-w-[82%]">
                <span className="label ml-0.5">Nova</span>
                <div className="bg-cosmos-800 border border-white/8 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-cosmos-50 leading-relaxed">
                  {msg.content || (msg.streaming ? (
                    <span className="flex gap-1 items-center h-4">
                      <span className="w-1 h-1 rounded-full bg-cosmos-300 animate-bounce" style={{animationDelay:'0ms'}} />
                      <span className="w-1 h-1 rounded-full bg-cosmos-300 animate-bounce" style={{animationDelay:'120ms'}} />
                      <span className="w-1 h-1 rounded-full bg-cosmos-300 animate-bounce" style={{animationDelay:'240ms'}} />
                    </span>
                  ) : '')}
                </div>
              </div>
            )}
            {msg.role === 'user' && (
              <div className="max-w-[82%] bg-nova-blue/15 border border-nova-blue/20 rounded-2xl rounded-tr-sm px-4 py-3 text-sm text-cosmos-50 leading-relaxed">
                {msg.content}
              </div>
            )}
          </div>
        ))}

        {toolActivity && (
          <div className="flex justify-start">
            <span className="text-xs text-cosmos-300 bg-cosmos-700/60 border border-white/8 px-3 py-1.5 rounded-md">
              {toolActivity}...
            </span>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <div className="px-5 pb-5 pt-3 border-t border-white/8 shrink-0">
        {status !== 'active' && (
          <div className="text-center text-xs text-cosmos-300 mb-3 py-2 bg-cosmos-700/40 rounded-md border border-white/8">
            {status === 'escalated'
              ? 'Your case has been escalated. A support agent will follow up shortly.'
              : 'This conversation has ended.'}
          </div>
        )}
        <div className="flex gap-2 items-end">
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isStreaming || status !== 'active' || isStarting}
            placeholder="Message Nova..."
            rows={1}
            className="field resize-none leading-relaxed"
            style={{ minHeight: 42, maxHeight: 120, overflowY: 'auto' }}
          />
          <button
            onClick={sendMessage}
            disabled={!canSend}
            className="btn-primary shrink-0"
            style={{ height: 42, minWidth: 72 }}
          >
            {isStreaming ? (
              <span className="flex gap-0.5 justify-center items-center">
                <span className="w-1 h-1 rounded-full bg-current animate-bounce" style={{animationDelay:'0ms'}} />
                <span className="w-1 h-1 rounded-full bg-current animate-bounce" style={{animationDelay:'80ms'}} />
                <span className="w-1 h-1 rounded-full bg-current animate-bounce" style={{animationDelay:'160ms'}} />
              </span>
            ) : 'Send'}
          </button>
        </div>
      </div>
    </div>
  )
}
