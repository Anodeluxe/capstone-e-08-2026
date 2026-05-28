'use client'

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts'
import { format } from 'date-fns'
import { id as idLocale } from 'date-fns/locale'

interface TrendPoint {
  hour: string
  avg_score: number | null
  avg_ph?: number | null
  avg_turbidity?: number | null
  avg_tds?: number | null
}

interface Props {
  data: TrendPoint[]
  threshold?: number
  title?: string
}

export default function TrendChart({ data, threshold = 60, title = 'Tren Skor 24 Jam Terakhir' }: Props) {
  return (
    <div className="rounded-xl border bg-white dark:bg-zinc-900 p-4 shadow-sm">
      <h3 className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-3">{title}</h3>
      {data.length === 0 ? (
        <div className="flex items-center justify-center h-48 text-sm text-zinc-400">
          Tidak ada data
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={240}>
          <AreaChart data={data} margin={{ top: 4, right: 24, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="scoreGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
            <XAxis
              dataKey="hour"
              tickFormatter={(v: string) => format(new Date(v), 'HH:mm', { locale: idLocale })}
              tick={{ fontSize: 10 }}
              interval="preserveStartEnd"
              minTickGap={40}
            />
            <YAxis tick={{ fontSize: 10 }} domain={[0, 100]} width={32} />
            <Tooltip
              labelFormatter={(v: unknown) =>
                format(new Date(v as string), 'dd MMM yyyy HH:mm', { locale: idLocale })
              }
              formatter={(value: unknown) => [
                value != null ? (value as number).toFixed(1) : '—',
                'Skor Rata-rata',
              ]}
              contentStyle={{ fontSize: 12 }}
            />
            <ReferenceLine
              y={threshold}
              stroke="#ef4444"
              strokeDasharray="4 4"
              label={{ value: `Batas ${threshold}`, position: 'insideTopRight', fontSize: 10, fill: '#ef4444' }}
            />
            <Area
              type="monotone"
              dataKey="avg_score"
              stroke="#3b82f6"
              strokeWidth={2}
              fill="url(#scoreGradient)"
              connectNulls
              dot={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
