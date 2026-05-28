'use client'

import { cn } from '@/lib/utils'
import { useWSStore } from '@/hooks/useSensorWebSocket'
import { useDashboardSummary } from '@/hooks/useSensorData'

function formatAge(seconds: number | null): string {
  if (seconds === null) return 'Tidak diketahui'
  if (seconds < 60) return `${Math.round(seconds)}d yang lalu`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m yang lalu`
  return `${Math.floor(minutes / 60)}j yang lalu`
}

export default function SystemStatus() {
  const { status } = useWSStore()
  const { data } = useDashboardSummary()

  const mqttConnected = data?.system_status.mqtt_connected ?? false
  const age = data?.system_status.last_reading_age_seconds ?? null

  return (
    <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-zinc-600 dark:text-zinc-400 rounded-lg border bg-white dark:bg-zinc-900 px-4 py-3">
      <div className="flex items-center gap-1.5">
        <span className={cn('w-2 h-2 rounded-full', mqttConnected ? 'bg-green-500' : 'bg-red-500')} />
        <span>MQTT: {mqttConnected ? 'Terhubung' : 'Terputus'}</span>
      </div>
      <div className="flex items-center gap-1.5">
        <span
          className={cn(
            'w-2 h-2 rounded-full',
            status === 'connected' ? 'bg-green-500' : status === 'connecting' ? 'bg-yellow-400 animate-pulse' : 'bg-red-500',
          )}
        />
        <span>
          WebSocket:{' '}
          {status === 'connected' ? 'Live' : status === 'connecting' ? 'Menghubungkan...' : 'Terputus'}
        </span>
      </div>
      <div className="flex items-center gap-1.5">
        <span>Pembacaan terakhir: {formatAge(age)}</span>
      </div>
      {data && (
        <div className="flex items-center gap-1.5">
          <span>Anomali (24j): {data.anomaly_count_24h}</span>
        </div>
      )}
    </div>
  )
}
