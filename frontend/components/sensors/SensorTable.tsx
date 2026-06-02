'use client'

import { format, parseISO } from 'date-fns'
import { id as idLocale } from 'date-fns/locale'
import { cn } from '@/lib/utils'
import type { SensorReading } from '@/types'

interface Props {
  data: SensorReading[]
}

function scoreClass(score: number | null): string {
  if (score === null) return 'text-muted-foreground'
  if (score >= 75) return 'text-emerald-600 dark:text-emerald-400 font-medium'
  if (score >= 60) return 'text-amber-600 dark:text-amber-400 font-medium'
  return 'text-rose-600 dark:text-rose-400 font-medium'
}

export default function SensorTable({ data }: Props) {
  if (data.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4">Tidak ada data tersedia.</p>
    )
  }

  return (
    <div
      className="rounded-xl border border-border bg-card overflow-hidden"
      style={{ boxShadow: '0 2px 12px -4px oklch(0.4 0.1 220 / 0.08)' }}
    >
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/50 text-muted-foreground text-left">
              <th className="px-4 py-3 font-medium">Waktu</th>
              <th className="px-4 py-3 font-medium">pH</th>
              <th className="px-4 py-3 font-medium">Turbiditas</th>
              <th className="px-4 py-3 font-medium">TDS</th>
              <th className="px-4 py-3 font-medium">Suhu</th>
              <th className="px-4 py-3 font-medium">Level Air</th>
              <th className="px-4 py-3 font-medium">Skor</th>
              <th className="px-4 py-3 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {data.map((row) => (
              <tr
                key={row.id}
                className={cn(
                  'border-b border-border/60 last:border-0 transition-colors',
                  row.is_sudden_change
                    ? 'bg-rose-50/60 dark:bg-rose-950/20'
                    : 'hover:bg-muted/40',
                )}
              >
                <td className="px-4 py-2 text-muted-foreground whitespace-nowrap text-xs font-mono">
                  {format(parseISO(row.timestamp), 'dd MMM HH:mm:ss', { locale: idLocale })}
                </td>
                <td className="px-4 py-2 font-mono tabular-nums">{row.ph.toFixed(2)}</td>
                <td className="px-4 py-2 font-mono tabular-nums">{row.turbidity.toFixed(1)} NTU</td>
                <td className="px-4 py-2 font-mono tabular-nums">{row.tds.toFixed(0)} ppm</td>
                <td className="px-4 py-2 font-mono tabular-nums">{row.temperature.toFixed(1)} °C</td>
                <td className="px-4 py-2 font-mono tabular-nums">{row.water_level.toFixed(1)}%</td>
                <td className={cn('px-4 py-2 font-mono tabular-nums', scoreClass(row.score_overall))}>
                  {row.score_overall !== null ? row.score_overall.toFixed(1) : '—'}
                </td>
                <td className="px-4 py-2">
                  {row.is_sudden_change ? (
                    <span className="text-xs bg-rose-100 text-rose-700 dark:bg-rose-950/50 dark:text-rose-300 px-1.5 py-0.5 rounded-full">
                      Anomali{row.anomaly_parameter ? `: ${row.anomaly_parameter}` : ''}
                    </span>
                  ) : (
                    <span className="text-xs text-muted-foreground">Normal</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
