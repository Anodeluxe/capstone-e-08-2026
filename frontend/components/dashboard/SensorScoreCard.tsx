'use client'

import { cn } from '@/lib/utils'
import type { ValveID } from '@/types'

export const VALVE_LABELS: Record<ValveID, string> = {
  bathroom: 'Kamar Mandi',
  kitchen: 'Dapur',
  laundry: 'Laundri',
  garden: 'Taman',
}

const CLOSE_THRESHOLDS: Record<ValveID, number> = {
  bathroom: 60,
  kitchen: 65,
  laundry: 45,
  garden: 30,
}

function scoreColor(score: number): { stroke: string; fill: string; labelClass: string } {
  if (score >= 75) return {
    stroke: '#10b981',
    fill: '#10b981',
    labelClass: 'text-emerald-600 dark:text-emerald-400',
  }
  if (score >= 60) return {
    stroke: '#d97706',
    fill: '#d97706',
    labelClass: 'text-amber-600 dark:text-amber-400',
  }
  if (score >= 45) return {
    stroke: '#f97316',
    fill: '#f97316',
    labelClass: 'text-orange-500 dark:text-orange-400',
  }
  return {
    stroke: '#f43f5e',
    fill: '#f43f5e',
    labelClass: 'text-rose-500 dark:text-rose-400',
  }
}

const R = 38
const CIRCUMFERENCE = 2 * Math.PI * R

interface Props {
  valveId: ValveID
  score: number | null
  isOpen: boolean
}

export default function SensorScoreCard({ valveId, score, isOpen }: Props) {
  const displayScore = score ?? 0
  const { stroke, fill, labelClass } = scoreColor(displayScore)
  const dashOffset = CIRCUMFERENCE - (displayScore / 100) * CIRCUMFERENCE
  const threshold = CLOSE_THRESHOLDS[valveId]
  const meetsThreshold = score !== null && score >= threshold

  return (
    <div
      className="flex flex-col items-center gap-2.5 rounded-xl border border-border bg-card p-4"
      style={{ boxShadow: '0 4px 20px -8px oklch(0.4 0.1 220 / 0.12)' }}
    >
      <svg
        width={96}
        height={96}
        viewBox="0 0 100 100"
        aria-label={`Skor ${VALVE_LABELS[valveId]}: ${score ?? 'tidak ada data'}`}
      >
        {/* Track */}
        <circle cx={50} cy={50} r={R} fill="none" stroke="currentColor" strokeWidth={7} className="text-border" />
        {/* Progress arc */}
        <circle
          cx={50}
          cy={50}
          r={R}
          fill="none"
          stroke={score === null ? 'currentColor' : stroke}
          className={score === null ? 'text-border' : undefined}
          strokeWidth={7}
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={score === null ? CIRCUMFERENCE : dashOffset}
          transform="rotate(-90 50 50)"
          style={{ transition: 'stroke-dashoffset 0.6s cubic-bezier(0.16, 1, 0.3, 1), stroke 0.3s ease' }}
        />
        {/* Score label */}
        <text
          x={50}
          y={55}
          textAnchor="middle"
          fontSize={18}
          fontWeight={700}
          fontFamily="var(--font-mono)"
          fill={score === null ? 'currentColor' : fill}
          className={score === null ? 'text-muted-foreground' : undefined}
        >
          {score === null ? '—' : Math.round(displayScore)}
        </text>
      </svg>

      <div className="text-center">
        <p className="font-medium text-sm text-foreground">{VALVE_LABELS[valveId]}</p>
        <p className={cn('text-xs mt-0.5', score === null ? 'text-muted-foreground' : labelClass)}>
          {score === null
            ? 'Tidak ada data'
            : meetsThreshold
              ? 'Memenuhi standar'
              : 'Di bawah batas'}
        </p>
        <p
          className={cn(
            'text-xs mt-0.5 font-medium',
            isOpen ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-500 dark:text-rose-400',
          )}
        >
          {isOpen ? 'Terbuka' : 'Tertutup'}
        </p>
      </div>
    </div>
  )
}
