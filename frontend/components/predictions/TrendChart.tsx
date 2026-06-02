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
    <div
      className="rounded-xl border border-border bg-card p-4"
      style={{ boxShadow: '0 2px 12px -4px oklch(0.4 0.1 220 / 0.08)' }}
    >
      <h3 className="text-sm font-medium text-foreground mb-3">{title}</h3>
      {data.length === 0 ? (
        <div className="flex items-center justify-center h-48 text-sm text-muted-foreground">
          Tidak ada data
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={240}>
          <AreaChart data={data} margin={{ top: 4, right: 24, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="scoreGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#0891b2" stopOpacity={0.18} />
                <stop offset="95%" stopColor="#0891b2" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.91 0.008 220)" opacity={0.6} />
            <XAxis
              dataKey="hour"
              tickFormatter={(v: string) => format(new Date(v), 'HH:mm', { locale: idLocale })}
              tick={{ fontSize: 10, fontFamily: 'var(--font-mono)' }}
              interval="preserveStartEnd"
              minTickGap={40}
              stroke="oklch(0.62 0.012 220)"
            />
            <YAxis
              tick={{ fontSize: 10, fontFamily: 'var(--font-mono)' }}
              domain={[0, 100]}
              width={32}
              stroke="oklch(0.62 0.012 220)"
            />
            <Tooltip
              labelFormatter={(v: unknown) =>
                format(new Date(v as string), 'dd MMM yyyy HH:mm', { locale: idLocale })
              }
              formatter={(value: unknown) => [
                value != null ? (value as number).toFixed(1) : '—',
                'Skor Rata-rata',
              ]}
              contentStyle={{
                fontSize: 12,
                fontFamily: 'var(--font-mono)',
                background: 'var(--card)',
                border: '1px solid var(--border)',
                borderRadius: '8px',
                color: 'var(--foreground)',
              }}
            />
            <ReferenceLine
              y={threshold}
              stroke="#f43f5e"
              strokeDasharray="4 4"
              label={{ value: `Batas ${threshold}`, position: 'insideTopRight', fontSize: 10, fill: '#f43f5e' }}
            />
            <Area
              type="monotone"
              dataKey="avg_score"
              stroke="#0891b2"
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
