'use client'

import { useState } from 'react'
import { cn, toUtcDate } from '@/lib/utils'
import { VALVE_LABELS } from '@/components/dashboard/SensorScoreCard'
import OverrideModal from './OverrideModal'
import type { ValveState } from '@/types'
import { format } from 'date-fns'
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
            <h3 className="font-medium text-foreground">{VALVE_LABELS[valve.id] ?? valve.id}</h3>
            <p className="text-xs text-muted-foreground font-mono mt-0.5">{valve.id}</p>
          </div>
          <button
            onClick={handleToggle}
            className={cn(
              'min-h-[36px] px-3.5 py-1.5 sm:min-h-0 sm:py-1 rounded-md text-xs font-medium transition-colors',
              valve.is_open
                ? 'bg-rose-100 text-rose-700 hover:bg-rose-200 dark:bg-rose-950/60 dark:text-rose-300'
                : 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300',
            )}
          >
            {valve.is_open ? 'Tutup' : 'Buka'}
          </button>
        </div>

        <div className="flex items-center justify-between text-xs pt-3 border-t border-border">
          <span
            className={cn(
              'px-2 py-0.5 rounded-full font-medium',
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
          {(() => {
            const d = toUtcDate(valve.last_changed_at)
            return d ? format(d, 'dd MMM HH:mm', { locale: idLocale }) : valve.last_changed_at
          })()}
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
