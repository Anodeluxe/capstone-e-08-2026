'use client'

import { useState } from 'react'
import { Power, PowerOff } from 'lucide-react'
import { cn, toUtcDate } from '@/lib/utils'
import { VALVE_LABELS } from '@/components/dashboard/SensorScoreCard'
import { Button } from '@/components/ui/button'
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

  const isOpen = valve.is_open
  const changedAt = toUtcDate(valve.last_changed_at)

  function handleToggle() {
    setPendingAction(isOpen ? 'close' : 'open')
    setModalOpen(true)
  }

  return (
    <>
      <div
        className="flex flex-col rounded-xl border border-border bg-card p-4"
        style={{ boxShadow: '0 2px 12px -4px oklch(0.4 0.1 220 / 0.08)' }}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="font-medium text-foreground truncate">{VALVE_LABELS[valve.id] ?? valve.id}</h3>
            <p className="text-xs text-muted-foreground font-mono mt-0.5 truncate">{valve.id}</p>
          </div>
          <span
            className={cn(
              'inline-flex shrink-0 items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium',
              isOpen
                ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300'
                : 'bg-rose-100 text-rose-700 dark:bg-rose-950/50 dark:text-rose-300',
            )}
          >
            <span className={cn('size-1.5 rounded-full', isOpen ? 'bg-emerald-500' : 'bg-rose-500')} />
            {isOpen ? 'Terbuka' : 'Tertutup'}
          </span>
        </div>

        <dl className="mt-3 flex items-center justify-between gap-2 text-xs">
          <dt className="text-muted-foreground">Terakhir diubah</dt>
          <dd className="font-mono tabular-nums text-muted-foreground">
            {changedAt ? format(changedAt, 'dd MMM HH:mm', { locale: idLocale }) : '—'}
          </dd>
        </dl>

        {valve.quality_score_at_close !== null && (
          <dl className="mt-1 flex items-center justify-between gap-2 text-xs">
            <dt className="text-muted-foreground">Skor saat ditutup</dt>
            <dd className="font-mono tabular-nums text-muted-foreground">
              {valve.quality_score_at_close.toFixed(1)}
            </dd>
          </dl>
        )}

        <Button
          onClick={handleToggle}
          variant={isOpen ? 'outline' : 'default'}
          className={cn(
            'mt-4 h-10 w-full gap-2',
            isOpen &&
              'border-rose-200 text-rose-700 hover:bg-rose-50 dark:border-rose-900/60 dark:text-rose-300 dark:hover:bg-rose-950/40',
          )}
        >
          {isOpen ? <PowerOff className="size-4" /> : <Power className="size-4" />}
          {isOpen ? 'Tutup Katup' : 'Buka Katup'}
        </Button>
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
