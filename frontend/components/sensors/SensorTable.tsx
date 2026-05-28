'use client'

import { format, parseISO } from 'date-fns'
import { id as idLocale } from 'date-fns/locale'
import { cn } from '@/lib/utils'
import type { SensorReading } from '@/types'

interface Props {
  data: SensorReading[]
}

function scoreClass(score: number | null): string {
  if (score === null) return 'text-zinc-400'
  if (score >= 75) return 'text-green-600 font-medium'
  if (score >= 60) return 'text-yellow-600 font-medium'
  return 'text-red-600 font-medium'
}

export default function SensorTable({ data }: Props) {
  if (data.length === 0) {
    return (
      <p className="text-sm text-zinc-400 py-4">Tidak ada data tersedia.</p>
    )
  }

  return (
    <div className="rounded-xl border bg-white dark:bg-zinc-900 overflow-hidden shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-zinc-50 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 text-left">
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
                  'border-b last:border-0 transition-colors',
                  row.is_sudden_change
                    ? 'bg-red-50 dark:bg-red-950/40'
                    : 'hover:bg-zinc-50 dark:hover:bg-zinc-800/50',
                )}
              >
                <td className="px-4 py-2 text-zinc-500 whitespace-nowrap text-xs">
                  {format(parseISO(row.timestamp), 'dd MMM HH:mm:ss', { locale: idLocale })}
                </td>
                <td className="px-4 py-2">{row.ph.toFixed(2)}</td>
                <td className="px-4 py-2">{row.turbidity.toFixed(1)} NTU</td>
                <td className="px-4 py-2">{row.tds.toFixed(0)} ppm</td>
                <td className="px-4 py-2">{row.temperature.toFixed(1)} °C</td>
                <td className="px-4 py-2">{row.water_level.toFixed(1)}%</td>
                <td className={cn('px-4 py-2', scoreClass(row.score_overall))}>
                  {row.score_overall !== null ? row.score_overall.toFixed(1) : '—'}
                </td>
                <td className="px-4 py-2">
                  {row.is_sudden_change ? (
                    <span className="text-xs bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300 px-1.5 py-0.5 rounded-full">
                      Anomali{row.anomaly_parameter ? `: ${row.anomaly_parameter}` : ''}
                    </span>
                  ) : (
                    <span className="text-xs text-zinc-400">Normal</span>
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
