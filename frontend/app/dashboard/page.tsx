'use client'

import { useDashboardSummary } from '@/hooks/useSensorData'
import { useWSStore } from '@/hooks/useSensorWebSocket'
import AlertBanner from '@/components/dashboard/AlertBanner'
import SensorScoreCard from '@/components/dashboard/SensorScoreCard'
import SystemStatus from '@/components/dashboard/SystemStatus'
import TrendChart from '@/components/predictions/TrendChart'
import type { ValveID } from '@/types'

const VALVE_IDS: ValveID[] = ['bathroom', 'kitchen', 'laundry', 'garden']

export default function DashboardPage() {
  const { data, isLoading } = useDashboardSummary()
  const { latestReading } = useWSStore()

  // WS reading takes precedence over polled data for live scores
  const liveScores: Record<ValveID, number | null> = {
    bathroom: latestReading?.score_bathroom ?? data?.latest_reading?.score_bathroom ?? null,
    kitchen: latestReading?.score_kitchen ?? data?.latest_reading?.score_kitchen ?? null,
    laundry: latestReading?.score_laundry ?? data?.latest_reading?.score_laundry ?? null,
    garden: latestReading?.score_garden ?? data?.latest_reading?.score_garden ?? null,
  }

  const valveMap = Object.fromEntries((data?.valve_states ?? []).map((v) => [v.id, v]))
  const latest = latestReading ?? data?.latest_reading

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Monitoring kualitas air toren secara real-time</p>
      </div>

      <SystemStatus />
      <AlertBanner />

      <section>
        <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-widest mb-3">
          Skor Kualitas per Titik Distribusi
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {VALVE_IDS.map((id) => (
            <SensorScoreCard
              key={id}
              valveId={id}
              score={liveScores[id]}
              isOpen={valveMap[id]?.is_open ?? false}
            />
          ))}
        </div>
      </section>

      {latest && (
        <section>
          <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-widest mb-3">
            Pembacaan Sensor Terkini
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {[
              { label: 'pH', value: latest.ph.toFixed(2), unit: '' },
              { label: 'Turbiditas', value: latest.turbidity.toFixed(1), unit: ' NTU' },
              { label: 'TDS', value: latest.tds.toFixed(0), unit: ' ppm' },
              { label: 'Suhu', value: latest.temperature.toFixed(1), unit: ' °C' },
              { label: 'Level Air', value: latest.water_level.toFixed(1), unit: '%' },
            ].map(({ label, value, unit }) => (
              <div
                key={label}
                className="rounded-xl border border-border bg-card px-4 py-3"
                style={{ boxShadow: '0 2px 12px -4px oklch(0.4 0.1 220 / 0.08)' }}
              >
                <p className="text-xs text-muted-foreground mb-0.5">{label}</p>
                <p className="text-2xl font-bold font-mono tracking-tight tabular-nums">
                  {value}
                  <span className="text-sm font-normal text-muted-foreground ml-0.5">{unit}</span>
                </p>
              </div>
            ))}
          </div>
        </section>
      )}

      {isLoading ? (
        <div className="h-64 rounded-xl border border-border bg-card animate-pulse" />
      ) : (
        <TrendChart data={data?.trend_24h ?? []} />
      )}
    </div>
  )
}
