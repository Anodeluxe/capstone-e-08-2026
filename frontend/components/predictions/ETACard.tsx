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
  if (days === null) return 'text-muted-foreground'
  if (days <= 1) return 'text-rose-600 dark:text-rose-400'
  if (days <= 3) return 'text-orange-500 dark:text-orange-400'
  if (days <= 7) return 'text-amber-600 dark:text-amber-400'
  return 'text-emerald-600 dark:text-emerald-400'
}

export default function ETACard({ prediction, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="rounded-xl border border-border bg-card p-6 animate-pulse space-y-3">
        <div className="h-3 bg-muted rounded w-1/2" />
        <div className="h-10 bg-muted rounded w-2/3" />
        <div className="h-3 bg-muted rounded w-1/3" />
      </div>
    )
  }

  if (!prediction) {
    return (
      <div className="rounded-xl border border-border bg-card p-6 flex items-center justify-center">
        <p className="text-sm text-muted-foreground">Data prediksi tidak tersedia.</p>
      </div>
    )
  }

  const { days_until_threshold: days, predicted_date, confidence, model_used } = prediction
  const confidencePct = confidence !== null ? (confidence * 100).toFixed(0) : null

  return (
    <div
      className="rounded-xl border border-border bg-card p-6"
      style={{ boxShadow: '0 2px 12px -4px oklch(0.4 0.1 220 / 0.08)' }}
    >
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-widest mb-2">
        Estimasi Degradasi Air
      </p>
      <p className={cn('text-4xl font-bold font-mono tabular-nums mb-1', urgencyClass(days))}>
        {days !== null ? `${days.toFixed(1)}` : '—'}
        <span className="text-xl font-normal ml-1">hari</span>
      </p>
      {predicted_date && (
        <p className="text-sm text-muted-foreground mb-4">
          Perkiraan: {format(parseISO(predicted_date), 'dd MMMM yyyy', { locale: idLocale })}
        </p>
      )}
      <div className="flex flex-wrap gap-3 text-xs text-muted-foreground border-t border-border pt-3">
        <span>
          Model: <span className="text-foreground font-mono">{model_used}</span>
        </span>
        {confidencePct !== null && (
          <span>
            Kepercayaan: <span className="text-foreground font-mono">{confidencePct}%</span>
          </span>
        )}
      </div>
    </div>
  )
}
