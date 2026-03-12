import { useEffect, useRef, useState, useCallback } from 'react'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'

export interface WSMessage {
  type: string
  run_id?: string
  status?: string
  agent?: string
  metrics?: Record<string, number | null>
  anomalies?: AnomalyItem[]
  completed_agents?: string[]
  errors?: { agent: string; error: string }[]
  data?: Record<string, unknown>
  executive_summary?: string
}

export interface AnomalyItem {
  transaction_date: string
  description: string
  amount: number
  severity: 'low' | 'medium' | 'high' | 'critical'
  reason: string
  recommended_action: string
  anomaly_score: number
}

type Status = 'connecting' | 'open' | 'closed' | 'error'

export function useWebSocket() {
  const ws = useRef<WebSocket | null>(null)
  const [status, setStatus] = useState<Status>('connecting')
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return

    ws.current = new WebSocket(WS_URL)

    ws.current.onopen = () => setStatus('open')

    ws.current.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data as string)
        setLastMessage(msg)
      } catch {
        // ignore malformed messages
      }
    }

    ws.current.onerror = () => setStatus('error')

    ws.current.onclose = () => {
      setStatus('closed')
      // Reconnect after 3 s
      reconnectTimer.current = setTimeout(connect, 3000)
    }
  }, [])

  useEffect(() => {
    connect()
    return () => {
      reconnectTimer.current && clearTimeout(reconnectTimer.current)
      ws.current?.close()
    }
  }, [connect])

  return { status, lastMessage }
}
