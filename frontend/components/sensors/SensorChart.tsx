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
  color = '#3b82f6',
  unit = '',
}: Props) {
  return (
    <div className="rounded-xl border bg-white dark:bg-zinc-900 p-4 shadow-sm">
      <h3 className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-3">{label}</h3>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
          <XAxis
            dataKey="timestamp"
            tickFormatter={(v: string) => format(parseISO(v), 'HH:mm', { locale: idLocale })}
            tick={{ fontSize: 10 }}
            interval="preserveStartEnd"
            minTickGap={40}
          />
          <YAxis tick={{ fontSize: 10 }} width={42} unit={unit} />
          <Tooltip
            labelFormatter={(v: unknown) =>
              format(parseISO(v as string), 'dd MMM yyyy HH:mm', { locale: idLocale })
            }
            formatter={(value: unknown) => [`${value as number}${unit}`, label]}
            contentStyle={{ fontSize: 12 }}
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
