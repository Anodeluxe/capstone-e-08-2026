'use client'

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { format, parseISO } from 'date-fns'
import { id as idLocale } from 'date-fns/locale'
import type { SensorReading } from '@/types'

type SensorNumericKey = keyof Pick<
  SensorReading,
  'ph' | 'turbidity' | 'tds' | 'temperature' | 'water_level' | 'score_overall'
>

interface Props {
  data: SensorReading[]
  dataKey: SensorNumericKey
  label: string
  color?: string
  unit?: string
}

export default function SensorChart({
  data,
  dataKey,
  label,
  color = '#0891b2',
  unit = '',
}: Props) {
  return (
    <div
      className="rounded-xl border border-border bg-card p-4"
      style={{ boxShadow: '0 2px 12px -4px oklch(0.4 0.1 220 / 0.08)' }}
    >
      <h3 className="text-sm font-medium text-foreground mb-3">{label}</h3>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.91 0.008 220)" opacity={0.6} />
          <XAxis
            dataKey="timestamp"
            tickFormatter={(v: string) => format(parseISO(v), 'HH:mm', { locale: idLocale })}
            tick={{ fontSize: 10, fontFamily: 'var(--font-mono)' }}
            interval="preserveStartEnd"
            minTickGap={40}
            stroke="oklch(0.62 0.012 220)"
          />
          <YAxis
            tick={{ fontSize: 10, fontFamily: 'var(--font-mono)' }}
            width={42}
            unit={unit}
            stroke="oklch(0.62 0.012 220)"
          />
          <Tooltip
            labelFormatter={(v: unknown) =>
              format(parseISO(v as string), 'dd MMM yyyy HH:mm', { locale: idLocale })
            }
            formatter={(value: unknown) => [`${value as number}${unit}`, label]}
            contentStyle={{
              fontSize: 12,
              fontFamily: 'var(--font-mono)',
              background: 'var(--card)',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              color: 'var(--foreground)',
            }}
          />
          <Line
            type="monotone"
            dataKey={dataKey as string}
            stroke={color}
            dot={false}
            strokeWidth={2}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
