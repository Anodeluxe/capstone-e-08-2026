'use client'

import { useMemo, useState } from 'react'
import { useSensorHistory, useSensorHourly, useSensorAnomalies } from '@/hooks/useSensorData'
import { useWSStore } from '@/hooks/useSensorWebSocket'
import SensorChart from '@/components/sensors/SensorChart'
import SensorTable from '@/components/sensors/SensorTable'
import type { HourlySensorReading, SensorReading } from '@/types'

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

type ViewMode = '6h' | '24h' | '48h' | '72h' | 'hourly'

const VIEW_OPTIONS: Array<{ value: ViewMode; label: string }> = [
  { value: '6h', label: '6 jam terakhir' },
  { value: '24h', label: '24 jam terakhir' },
  { value: '48h', label: '48 jam terakhir' },
  { value: '72h', label: '72 jam terakhir' },
  { value: 'hourly', label: '7 hari (rata-rata per jam)' },
]

const HOURLY_HOURS = 168

export default function SensorsPage() {
  const [view, setView] = useState<ViewMode>('24h')
  const isHourly = view === 'hourly'
  const hours = isHourly ? HOURLY_HOURS : Number.parseInt(view, 10)

  const { data: history, isLoading: historyLoading } = useSensorHistory(hours, !isHourly)
  const { data: hourly, isLoading: hourlyLoading } = useSensorHourly(HOURLY_HOURS, isHourly)
  const { data: anomalies } = useSensorAnomalies(72)
  const { latestReading } = useWSStore()

  const isLoading = isHourly ? hourlyLoading : historyLoading

  // Chart: raw readings for the 6/24/48/72h views, hourly averages otherwise.
  const chartData: Array<SensorReading | HourlySensorReading> = isHourly
    ? hourly ?? []
    : history ?? []

  // History dari API urut lama → baru (ascending). Tabel "Pembacaan Terbaru"
  // harus menampilkan data TERAKHIR dengan yang terbaru di atas. Reading live
  // dari WebSocket hanya digabung pada mode mentah (bukan mode per jam).
  const latestRows = useMemo(() => {
    if (isHourly) return (hourly ?? []).slice().reverse()

    const rows: SensorReading[] = history ?? []
    const merged =
      latestReading && !rows.some((r) => r.id === latestReading.id)
        ? [...rows, latestReading]
        : rows
    return merged.slice(-50).reverse()
  }, [history, hourly, isHourly, latestReading])

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Data Sensor</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Riwayat pembacaan sensor</p>
        </div>
        <select
          value={view}
          onChange={(e) => setView(e.target.value as ViewMode)}
          className="h-9 rounded-md border border-input bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring text-foreground w-full sm:w-auto"
        >
          {VIEW_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
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
              data={chartData}
              dataKey={dataKey}
              label={label}
              color={color}
              unit={unit}
              connectNulls={!isHourly}
            />
          ))}
        </div>
      )}

      <section>
        <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-widest mb-3">
          {isHourly
            ? 'Rata-rata per Jam (7 hari terakhir)'
            : `Pembacaan Terbaru (${hours} jam terakhir)`}
        </h2>
        <SensorTable data={latestRows} showSampleCount={isHourly} />
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
