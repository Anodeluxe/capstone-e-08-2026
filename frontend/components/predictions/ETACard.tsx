'use client'

import { format, parseISO } from 'date-fns'
import { id as idLocale } from 'date-fns/locale'
import { cn } from '@/lib/utils'
import type { PredictionResult } from '@/types'

interface Props {
  prediction: PredictionResult | null
  isLoading?: boolean
}

function urgencyClass(days: number | null): string {
  if (days === null) return 'text-zinc-400'
  if (days <= 1) return 'text-red-600'
  if (days <= 3) return 'text-orange-500'
  if (days <= 7) return 'text-yellow-600'
  return 'text-green-600'
}

export default function ETACard({ prediction, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="rounded-xl border bg-white dark:bg-zinc-900 p-6 shadow-sm animate-pulse space-y-3">
        <div className="h-3 bg-zinc-200 dark:bg-zinc-700 rounded w-1/2" />
        <div className="h-10 bg-zinc-200 dark:bg-zinc-700 rounded w-2/3" />
        <div className="h-3 bg-zinc-200 dark:bg-zinc-700 rounded w-1/3" />
      </div>
    )
  }

  if (!prediction) {
    return (
      <div className="rounded-xl border bg-white dark:bg-zinc-900 p-6 shadow-sm flex items-center justify-center">
        <p className="text-sm text-zinc-400">Data prediksi tidak tersedia.</p>
      </div>
    )
  }

  const { days_until_threshold: days, predicted_date, confidence, model_used } = prediction
  const confidencePct = confidence !== null ? (confidence * 100).toFixed(0) : null

  return (
    <div className="rounded-xl border bg-white dark:bg-zinc-900 p-6 shadow-sm">
      <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-2">
        Estimasi Degradasi Air
      </p>
      <p className={cn('text-4xl font-bold mb-1', urgencyClass(days))}>
        {days !== null ? `${days.toFixed(1)} hari` : '—'}
      </p>
      {predicted_date && (
        <p className="text-sm text-zinc-600 dark:text-zinc-400 mb-4">
          Perkiraan: {format(parseISO(predicted_date), 'dd MMMM yyyy', { locale: idLocale })}
        </p>
      )}
      <div className="flex flex-wrap gap-3 text-xs text-zinc-400 border-t pt-3">
        <span>Model: <span className="text-zinc-600 dark:text-zinc-300">{model_used}</span></span>
        {confidencePct !== null && (
          <span>Kepercayaan: <span className="text-zinc-600 dark:text-zinc-300">{confidencePct}%</span></span>
        )}
      </div>
    </div>
  )
}
