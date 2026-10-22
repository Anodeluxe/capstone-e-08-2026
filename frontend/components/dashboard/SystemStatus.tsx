'use client'

import { useEffect, useState } from 'react'
import { cn, toUtcDate } from '@/lib/utils'
import { useWSStore } from '@/hooks/useSensorWebSocket'
import { useDashboardSummary } from '@/hooks/useSensorData'

function formatAge(seconds: number | null): string {
  if (seconds === null || isNaN(seconds)) return 'tidak diketahui'
  if (seconds < 60) return `${Math.max(0, Math.round(seconds))}d lalu`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m lalu`
  return `${Math.floor(minutes / 60)}j lalu`
}

export default function SystemStatus() {
  const { status, latestReading } = useWSStore()
  const { data } = useDashboardSummary()
  const [now, setNow] = useState<number>(Date.now())

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [])

  const mqttConnected = data?.system_status.mqtt_connected ?? false
  const anomalies = data?.anomaly_count_24h ?? 0

  // Hitung live age: prioritaskan timestamp dari WebSocket terbaru, lalu data polling
  const latestTs = latestReading?.timestamp ?? data?.latest_reading?.timestamp
  let age: number | null = null
  if (latestTs) {
    const d = toUtcDate(latestTs)
    if (d) {
      age = Math.max(0, (now - d.getTime()) / 1000)
    }
  } else if (data?.system_status?.last_reading_age_seconds != null) {
    age = data.system_status.last_reading_age_seconds
  }

  return (
    <div className="flex flex-wrap gap-x-5 gap-y-1.5 text-xs text-muted-foreground">
      <span className="flex items-center gap-1.5">
        <span className={cn('w-1.5 h-1.5 rounded-full shrink-0', mqttConnected ? 'bg-emerald-500' : 'bg-rose-500')} />
        MQTT {mqttConnected ? 'terhubung' : 'terputus'}
      </span>
      <span className="flex items-center gap-1.5">
        <span
          className={cn(
            'w-1.5 h-1.5 rounded-full shrink-0',
            status === 'connected' ? 'bg-emerald-500' : status === 'connecting' ? 'bg-amber-400 animate-pulse' : 'bg-rose-500',
          )}
        />
        WebSocket {status === 'connected' ? 'live' : status === 'connecting' ? 'menghubungkan' : 'terputus'}
      </span>
      <span>Pembacaan: {formatAge(age)}</span>
      {data && (
        <span className={cn(anomalies > 0 ? 'text-amber-600 dark:text-amber-400' : '')}>
          {anomalies} anomali (24j)
        </span>
      )}
    </div>
  )
}
