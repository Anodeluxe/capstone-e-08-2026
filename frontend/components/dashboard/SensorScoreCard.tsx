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

function scoreColor(score: number): { stroke: string; textClass: string } {
  if (score >= 75) return { stroke: '#22c55e', textClass: 'text-green-600' }
  if (score >= 60) return { stroke: '#eab308', textClass: 'text-yellow-600' }
  if (score >= 45) return { stroke: '#f97316', textClass: 'text-orange-500' }
  return { stroke: '#ef4444', textClass: 'text-red-600' }
}

const R = 40
const CIRCUMFERENCE = 2 * Math.PI * R

interface Props {
  valveId: ValveID
  score: number | null
  isOpen: boolean
}

export default function SensorScoreCard({ valveId, score, isOpen }: Props) {
  const displayScore = score ?? 0
  const { stroke, textClass } = scoreColor(displayScore)
  const dashOffset = CIRCUMFERENCE - (displayScore / 100) * CIRCUMFERENCE
  const threshold = CLOSE_THRESHOLDS[valveId]
  const meetsThreshold = score !== null && score >= threshold

  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border bg-white dark:bg-zinc-900 p-4 shadow-sm">
      <svg width={100} height={100} viewBox="0 0 100 100" aria-label={`Skor ${VALVE_LABELS[valveId]}: ${score ?? 'tidak ada data'}`}>
        {/* Track circle */}
        <circle cx={50} cy={50} r={R} fill="none" stroke="#e4e4e7" strokeWidth={8} />
        {/* Progress arc */}
        <circle
          cx={50}
          cy={50}
          r={R}
          fill="none"
          stroke={score === null ? '#e4e4e7' : stroke}
          strokeWidth={8}
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={score === null ? CIRCUMFERENCE : dashOffset}
          transform="rotate(-90 50 50)"
          style={{ transition: 'stroke-dashoffset 0.5s ease, stroke 0.3s ease' }}
        />
        {/* Score label */}
        <text
          x={50}
          y={55}
          textAnchor="middle"
          fontSize={20}
          fontWeight={700}
          fill={score === null ? '#a1a1aa' : stroke}
        >
          {score === null ? '—' : Math.round(displayScore)}
        </text>
      </svg>

      <div className="text-center">
        <p className="font-medium text-sm text-zinc-800 dark:text-zinc-100">{VALVE_LABELS[valveId]}</p>
        <p className={cn('text-xs mt-0.5', score === null ? 'text-zinc-400' : textClass)}>
          {score === null
            ? 'Tidak ada data'
            : meetsThreshold
              ? 'Memenuhi standar'
              : 'Di bawah batas'}
        </p>
        <p className={cn('text-xs mt-0.5 font-medium', isOpen ? 'text-green-600' : 'text-red-500')}>
          {isOpen ? 'Terbuka' : 'Tertutup'}
        </p>
      </div>
    </div>
  )
}
