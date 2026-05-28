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
      <div className="rounded-xl border bg-white dark:bg-zinc-900 p-4 shadow-sm">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="font-medium text-sm text-zinc-800 dark:text-zinc-100">
              {VALVE_LABELS[valve.id]}
            </h3>
            <p className="text-xs text-zinc-400 mt-0.5">
              Terakhir: {valve.last_changed_by}
            </p>
          </div>
          {/* Toggle switch */}
          <button
            onClick={handleToggle}
            className={cn(
              'relative shrink-0 w-12 h-6 rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1',
              valve.is_open
                ? 'bg-green-500 focus-visible:ring-green-400'
                : 'bg-zinc-300 dark:bg-zinc-600 focus-visible:ring-zinc-400',
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
                ? 'bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300'
                : 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300',
            )}
          >
            {valve.is_open ? 'Terbuka' : 'Tertutup'}
          </span>
          {valve.quality_score_at_close !== null && (
            <span className="text-xs text-zinc-500">
              Skor: {valve.quality_score_at_close.toFixed(1)}
            </span>
          )}
        </div>

        <p className="text-xs text-zinc-400 mt-2">
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
