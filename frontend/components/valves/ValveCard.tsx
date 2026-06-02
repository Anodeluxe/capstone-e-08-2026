'use client'

import { useState } from 'react'
import { cn } from '@/lib/utils'
import { VALVE_LABELS } from '@/components/dashboard/SensorScoreCard'
import OverrideModal from './OverrideModal'
import type { ValveState } from '@/types'
import { format, parseISO } from 'date-fns'
import { id as idLocale } from 'date-fns/locale'

interface Props {
  valve: ValveState
}

export default function ValveCard({ valve }: Props) {
  const [modalOpen, setModalOpen] = useState(false)
  const [pendingAction, setPendingAction] = useState<'open' | 'close'>('open')

  function handleToggle() {
    setPendingAction(valve.is_open ? 'close' : 'open')
    setModalOpen(true)
  }

  return (
    <>
      <div
        className="rounded-xl border border-border bg-card p-4"
        style={{ boxShadow: '0 2px 12px -4px oklch(0.4 0.1 220 / 0.08)' }}
      >
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="font-medium text-sm text-foreground">
              {VALVE_LABELS[valve.id]}
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Terakhir: {valve.last_changed_by}
            </p>
          </div>
          {/* Toggle switch */}
          <button
            onClick={handleToggle}
            className={cn(
              'relative shrink-0 w-12 h-6 rounded-full transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1',
              valve.is_open
                ? 'bg-emerald-500'
                : 'bg-muted-foreground/30',
            )}
            aria-label={valve.is_open ? 'Tutup katup' : 'Buka katup'}
            aria-pressed={valve.is_open}
          >
            <span
              className={cn(
                'absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow-sm transition-transform duration-150',
                valve.is_open ? 'translate-x-6' : 'translate-x-0',
              )}
            />
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span
            className={cn(
              'text-xs font-medium px-2 py-0.5 rounded-full',
              valve.is_open
                ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300'
                : 'bg-rose-100 text-rose-700 dark:bg-rose-950/50 dark:text-rose-300',
            )}
          >
            {valve.is_open ? 'Terbuka' : 'Tertutup'}
          </span>
          {valve.quality_score_at_close !== null && (
            <span className="text-xs text-muted-foreground font-mono">
              Skor: {valve.quality_score_at_close.toFixed(1)}
            </span>
          )}
        </div>

        <p className="text-xs text-muted-foreground mt-2 font-mono">
          {format(parseISO(valve.last_changed_at), 'dd MMM HH:mm', { locale: idLocale })}
        </p>
      </div>

      <OverrideModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        valve={valve}
        action={pendingAction}
      />
    </>
  )
}
