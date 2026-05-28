'use client'

import { X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useWSStore } from '@/hooks/useSensorWebSocket'
import type { AlertData } from '@/types'

const ALERT_STYLES: Record<AlertData['alert_type'], string> = {
  sudden_change: 'bg-red-50 border-red-300 text-red-800 dark:bg-red-950 dark:border-red-800 dark:text-red-200',
  early_warning: 'bg-yellow-50 border-yellow-300 text-yellow-800 dark:bg-yellow-950 dark:border-yellow-800 dark:text-yellow-200',
  valve_closed: 'bg-blue-50 border-blue-300 text-blue-800 dark:bg-blue-950 dark:border-blue-800 dark:text-blue-200',
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
            className="shrink-0 ml-auto opacity-70 hover:opacity-100 transition-opacity"
            aria-label="Tutup peringatan"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      ))}
    </div>
  )
}
