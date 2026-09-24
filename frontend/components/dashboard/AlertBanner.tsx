'use client'

import { useState } from 'react'
import { AlertTriangle, Clock, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useWSStore } from '@/hooks/useSensorWebSocket'
import { useLatestPredictions } from '@/hooks/useSensorData'
import type { AlertData } from '@/types'

const ALERT_STYLES: Record<AlertData['alert_type'], string> = {
  sudden_change: 'bg-rose-50 border-rose-200 text-rose-800 dark:bg-rose-950/40 dark:border-rose-800/60 dark:text-rose-200',
  early_warning: 'bg-amber-50 border-amber-200 text-amber-800 dark:bg-amber-950/40 dark:border-amber-800/60 dark:text-amber-200',
  valve_closed: 'bg-primary/5 border-primary/20 text-primary dark:bg-primary/10 dark:border-primary/30',
}

const ALERT_LABELS: Record<AlertData['alert_type'], string> = {
  sudden_change: 'Perubahan Mendadak',
  early_warning: 'Peringatan Dini',
  valve_closed: 'Katup Ditutup',
}

export default function AlertBanner() {
  const { alerts, dismissAlert } = useWSStore()
  const { data: predictions } = useLatestPredictions()
  const [dismissedEws, setDismissedEws] = useState(false)

  // Find the most urgent prediction with days_until_threshold <= 10
  const urgentPrediction = (!dismissedEws && Array.isArray(predictions))
    ? predictions.find(
        (p) => p.days_until_threshold !== null && p.days_until_threshold <= 10 && p.days_until_threshold >= 0,
      )
    : null

  if (alerts.length === 0 && !urgentPrediction) return null

  return (
    <div className="flex flex-col gap-2.5">
      {/* EWS RUL Countdown Banner */}
      {urgentPrediction && (
        <div
          className="flex items-start gap-3 rounded-lg border border-amber-400/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-900 dark:text-amber-200"
          role="alert"
        >
          <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
          <div className="flex-1 space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-semibold text-amber-950 dark:text-amber-100">
                Peringatan Dini EWS (Estimasi RUL):
              </span>
              <span className="inline-flex items-center gap-1 font-mono font-bold px-2 py-0.5 rounded bg-amber-200/60 dark:bg-amber-900/60 text-amber-950 dark:text-amber-100 text-xs">
                <Clock className="w-3.5 h-3.5" />
                {urgentPrediction.days_until_threshold !== null
                  ? `${urgentPrediction.days_until_threshold.toFixed(1)} Hari Tersisa`
                  : 'Mendekati Ambang'}
              </span>
              {urgentPrediction.confidence && (
                <span className="text-xs text-amber-800/80 dark:text-amber-300/80">
                  (Keyakinan Model: {(urgentPrediction.confidence * 100).toFixed(0)}%)
                </span>
              )}
            </div>
            <p className="text-xs sm:text-sm text-amber-900/90 dark:text-amber-200/90 leading-relaxed">
              Tren degradasi parameter <strong>{urgentPrediction.target_parameter.toUpperCase()}</strong>{' '}
              {urgentPrediction.valve_id ? `pada distribusi katup ${urgentPrediction.valve_id}` : 'pada toren'}{' '}
              diprediksi melampaui batas ambang mutu. Segera jadwalkan pembersihan toren atau kuras sedimen sebelum kualitas air memburuk.
            </p>
          </div>
          <button
            onClick={() => setDismissedEws(true)}
            className="shrink-0 ml-auto opacity-60 hover:opacity-100 transition-opacity focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
            aria-label="Tutup peringatan EWS"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* WebSocket Dynamic Alerts */}
      {alerts.map((alert, i) => (
        <div
          key={i}
          className={cn(
            'flex items-start gap-3 rounded-lg border px-4 py-3 text-sm',
            ALERT_STYLES[alert.alert_type],
          )}
          role="alert"
        >
          <span className="font-semibold shrink-0">{ALERT_LABELS[alert.alert_type]}:</span>
          <span className="flex-1">{alert.message}</span>
          <button
            onClick={() => dismissAlert(i)}
            className="shrink-0 ml-auto opacity-60 hover:opacity-100 transition-opacity focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
            aria-label="Tutup peringatan"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      ))}
    </div>
  )
}
