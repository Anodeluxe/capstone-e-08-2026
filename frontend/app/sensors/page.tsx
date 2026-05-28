'use client'

import { useState } from 'react'
import { useSensorHistory, useSensorAnomalies } from '@/hooks/useSensorData'
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
  { dataKey: 'ph', label: 'pH', color: '#8b5cf6', unit: '' },
  { dataKey: 'turbidity', label: 'Turbiditas (NTU)', color: '#f59e0b', unit: ' NTU' },
  { dataKey: 'tds', label: 'TDS (ppm)', color: '#10b981', unit: ' ppm' },
  { dataKey: 'temperature', label: 'Suhu (°C)', color: '#ef4444', unit: ' °C' },
  { dataKey: 'water_level', label: 'Level Air (%)', color: '#3b82f6', unit: '%' },
]

const HOUR_OPTIONS = [6, 24, 48, 72] as const

export default function SensorsPage() {
  const [hours, setHours] = useState<number>(24)
  const { data: history, isLoading } = useSensorHistory(hours)
  const { data: anomalies } = useSensorAnomalies(72)

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold">Data Sensor</h1>
          <p className="text-sm text-zinc-500 mt-0.5">Riwayat pembacaan sensor</p>
        </div>
        <select
          value={hours}
          onChange={(e) => setHours(Number(e.target.value))}
          className="rounded-md border px-3 py-1.5 text-sm bg-white dark:bg-zinc-900 dark:border-zinc-700 outline-none focus:ring-2 focus:ring-zinc-400"
        >
          {HOUR_OPTIONS.map((h) => (
            <option key={h} value={h}>{h} jam terakhir</option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <div className="grid sm:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-52 rounded-xl border bg-white dark:bg-zinc-900 animate-pulse" />
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
        <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-widest mb-3">
          Pembacaan Terbaru ({hours} jam terakhir)
        </h2>
        <SensorTable data={(history ?? []).slice(0, 50)} />
      </section>

      {(anomalies?.length ?? 0) > 0 && (
        <section>
          <h2 className="text-xs font-medium text-red-500 uppercase tracking-widest mb-3">
            Anomali Terdeteksi — 72 jam terakhir ({anomalies!.length} kejadian)
          </h2>
          <SensorTable data={anomalies!} />
        </section>
      )}
    </div>
  )
}
