'use client'

import { X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useWSStore } from '@/hooks/useSensorWebSocket'
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

  if (alerts.length === 0) return null

  return (
    <div className="flex flex-col gap-2">
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
