'use client'

import { useMemo, useState } from 'react'
import { useSensorHistory, useSensorAnomalies } from '@/hooks/useSensorData'
import { useWSStore } from '@/hooks/useSensorWebSocket'
import SensorChart from '@/components/sensors/SensorChart'
import SensorTable from '@/components/sensors/SensorTable'
import type { SensorReading } from '@/types'

type SensorNumericKey = keyof Pick<
  SensorReading,
  'ph' | 'turbidity' | 'tds' | 'temperature' | 'water_level'
>

const SENSOR_PARAMS: Array<{
  dataKey: SensorNumericKey
  label: string
  color: string
  unit: string
}> = [
  { dataKey: 'ph', label: 'pH', color: '#0891b2', unit: '' },              // cyan-600
  { dataKey: 'turbidity', label: 'Turbiditas (NTU)', color: '#d97706', unit: ' NTU' }, // amber-600
  { dataKey: 'tds', label: 'TDS (ppm)', color: '#059669', unit: ' ppm' },  // emerald-600
  { dataKey: 'temperature', label: 'Suhu (°C)', color: '#f43f5e', unit: ' °C' },       // rose-500
  { dataKey: 'water_level', label: 'Level Air (%)', color: '#6366f1', unit: '%' },     // indigo-500
]

const HOUR_OPTIONS = [6, 24, 48, 72] as const

export default function SensorsPage() {
  const [hours, setHours] = useState<number>(24)
  const { data: history, isLoading } = useSensorHistory(hours)
  const { data: anomalies } = useSensorAnomalies(72)
  const { latestReading } = useWSStore()

  // History dari API urut lama → baru (ascending). Tabel "Pembacaan Terbaru"
  // harus menampilkan 50 data TERAKHIR dengan yang terbaru di atas, dan
  // menyertakan reading live dari WebSocket agar update terasa realtime.
  const latestRows = useMemo(() => {
    const rows: SensorReading[] = history ?? []
    const merged =
      latestReading && !rows.some((r) => r.id === latestReading.id)
        ? [...rows, latestReading]
        : rows
    return merged.slice(-50).reverse()
  }, [history, latestReading])

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Data Sensor</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Riwayat pembacaan sensor</p>
        </div>
        <select
          value={hours}
          onChange={(e) => setHours(Number(e.target.value))}
          className="rounded-md border border-input bg-background px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-ring text-foreground"
        >
          {HOUR_OPTIONS.map((h) => (
            <option key={h} value={h}>{h} jam terakhir</option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <div className="grid sm:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-52 rounded-xl border border-border bg-card animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 gap-4">
          {SENSOR_PARAMS.map(({ dataKey, label, color, unit }) => (
            <SensorChart
              key={dataKey}
              data={history ?? []}
              dataKey={dataKey}
              label={label}
              color={color}
              unit={unit}
            />
          ))}
        </div>
      )}

      <section>
        <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-widest mb-3">
          Pembacaan Terbaru ({hours} jam terakhir)
        </h2>
        <SensorTable data={latestRows} />
      </section>

      {(anomalies?.length ?? 0) > 0 && (
        <section>
          <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-widest mb-3">
            <span className="text-rose-500">Anomali Terdeteksi</span> — 72 jam terakhir ({anomalies!.length} kejadian)
          </h2>
          <SensorTable data={anomalies!} />
        </section>
      )}
    </div>
  )
}
