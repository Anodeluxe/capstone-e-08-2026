'use client'

import { cn } from '@/lib/utils'
import { useWSStore } from '@/hooks/useSensorWebSocket'
import { useDashboardSummary } from '@/hooks/useSensorData'

function formatAge(seconds: number | null): string {
  if (seconds === null) return 'tidak diketahui'
  if (seconds < 60) return `${Math.round(seconds)}d lalu`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m lalu`
  return `${Math.floor(minutes / 60)}j lalu`
}

export default function SystemStatus() {
  const { status } = useWSStore()
  const { data } = useDashboardSummary()

  const mqttConnected = data?.system_status.mqtt_connected ?? false
  const age = data?.system_status.last_reading_age_seconds ?? null
  const anomalies = data?.anomaly_count_24h ?? 0

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
