'use client'

import { useEffect, useRef, useCallback } from 'react'
import { create } from 'zustand'
import type { SensorReading, ValveState, AlertData, ScoreBreakdown } from '@/types'

type ConnectionStatus = 'connecting' | 'connected' | 'disconnected'

interface SensorUpdate extends SensorReading {
  scores: ScoreBreakdown
}

interface ValveStatusEvent {
  valve_id: string
  is_open: boolean
  triggered_by: string
}

interface WSStore {
  status: ConnectionStatus
  latestReading: SensorUpdate | null
  valveStates: Record<string, ValveStatusEvent>
  alerts: AlertData[]
  setStatus: (s: ConnectionStatus) => void
  setLatestReading: (r: SensorUpdate) => void
  updateValveState: (v: ValveStatusEvent) => void
  pushAlert: (a: AlertData) => void
  dismissAlert: (index: number) => void
}

export const useWSStore = create<WSStore>((set) => ({
  status: 'disconnected',
  latestReading: null,
  valveStates: {},
  alerts: [],
  setStatus: (status) => set({ status }),
  setLatestReading: (latestReading) => set({ latestReading }),
  updateValveState: (v) =>
    set((state) => ({
      valveStates: { ...state.valveStates, [v.valve_id]: v },
    })),
  pushAlert: (a) =>
    set((state) => ({ alerts: [a, ...state.alerts].slice(0, 20) })),
  dismissAlert: (index) =>
    set((state) => ({
      alerts: state.alerts.filter((_, i) => i !== index),
    })),
}))

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost:8000/ws'
const PING_INTERVAL_MS = 30_000
const BASE_RECONNECT_DELAY_MS = 1_000
const MAX_RECONNECT_DELAY_MS = 30_000

export function useSensorWebSocket() {
  const wsRef = useRef<WebSocket | null>(null)
  const pingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectAttemptRef = useRef(0)
  const unmountedRef = useRef(false)

  const { setStatus, setLatestReading, updateValveState, pushAlert } = useWSStore()

  const clearPingTimer = () => {
    if (pingTimerRef.current) {
      clearInterval(pingTimerRef.current)
      pingTimerRef.current = null
    }
  }

  const clearReconnectTimer = () => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }
  }

  const connect = useCallback(() => {
    if (unmountedRef.current) return

    setStatus('connecting')
    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => {
      if (unmountedRef.current) { ws.close(); return }
      reconnectAttemptRef.current = 0
      setStatus('connected')

      pingTimerRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send('ping')
        }
      }, PING_INTERVAL_MS)
    }

    ws.onmessage = (event) => {
      if (typeof event.data !== 'string' || event.data === 'pong') return

      let parsed: { type: string; data: unknown }
      try {
        parsed = JSON.parse(event.data) as { type: string; data: unknown }
      } catch {
        return
      }

      switch (parsed.type) {
        case 'sensor_update':
          setLatestReading(parsed.data as SensorUpdate)
          break
        case 'valve_status':
          updateValveState(parsed.data as ValveStatusEvent)
          break
        case 'alert':
          pushAlert(parsed.data as AlertData)
          break
      }
    }

    ws.onclose = () => {
      clearPingTimer()
      if (unmountedRef.current) return

      setStatus('disconnected')

      const delay = Math.min(
        BASE_RECONNECT_DELAY_MS * 2 ** reconnectAttemptRef.current,
        MAX_RECONNECT_DELAY_MS,
      )
      reconnectAttemptRef.current += 1
      reconnectTimerRef.current = setTimeout(connect, delay)
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [setStatus, setLatestReading, updateValveState, pushAlert])

  useEffect(() => {
    unmountedRef.current = false
    connect()

    return () => {
      unmountedRef.current = true
      clearPingTimer()
      clearReconnectTimer()
      wsRef.current?.close()
    }
  }, [connect])

  return useWSStore()
}
