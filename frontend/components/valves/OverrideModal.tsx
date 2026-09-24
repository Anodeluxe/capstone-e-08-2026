'use client'

import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { useValveCommand } from '@/hooks/useValveControl'
import { VALVE_LABELS } from '@/components/dashboard/SensorScoreCard'
import type { ValveState } from '@/types'

interface Props {
  open: boolean
  onClose: () => void
  valve: ValveState
  action: 'open' | 'close'
}

export default function OverrideModal({ open, onClose, valve, action }: Props) {
  const [reason, setReason] = useState('')
  const { mutate, isPending } = useValveCommand()

  function handleConfirm() {
    mutate(
      { valveId: valve.id, payload: { action, reason: reason.trim() || undefined } },
      {
        onSuccess: () => {
          setReason('')
          onClose()
        },
      },
    )
  }

  function handleClose() {
    if (!isPending) {
      setReason('')
      onClose()
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && handleClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Override Manual Katup</DialogTitle>
          <DialogDescription>
            Anda akan{' '}
            <strong>{action === 'open' ? 'membuka' : 'menutup'}</strong> katup{' '}
            <strong>{VALVE_LABELS[valve.id]}</strong> secara manual. Tindakan ini
            menggantikan kontrol kualitas otomatis sistem.
          </DialogDescription>
        </DialogHeader>

        {action === 'close' && (
          <div className="rounded-md bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800/60 px-3 py-2 text-sm text-amber-800 dark:text-amber-200">
            Menutup katup secara manual dapat mempengaruhi distribusi air ke{' '}
            {VALVE_LABELS[valve.id].toLowerCase()}.
          </div>
        )}

        {action === 'open' && (
          <div className="rounded-md bg-rose-50/70 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800/50 px-3 py-2 text-sm text-rose-800 dark:text-rose-200">
            <strong>Peringatan Keamanan:</strong> Membuka katup secara manual mengabaikan proteksi otomatis sistem. Pastikan air aman sebelum membuka aliran ke pengguna.
          </div>
        )}

        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium block">
            Alasan Override <span className="text-muted-foreground font-normal">(disarankan untuk audit log)</span>
          </label>
          <input
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !isPending && handleConfirm()}
            placeholder="Pilih preset di bawah atau ketik alasan..."
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring placeholder:text-muted-foreground disabled:opacity-50"
            disabled={isPending}
          />
          <div className="flex flex-wrap gap-1.5 pt-1">
            {[
              'Pembersihan toren rutin',
              'Pengujian katup solenoid',
              'Kebutuhan mendesak operasional',
              'Kuras air terkontaminasi',
            ].map((preset) => (
              <button
                key={preset}
                type="button"
                onClick={() => setReason(preset)}
                className="text-xs px-2.5 py-1 rounded-md border border-border/80 bg-muted/50 hover:bg-muted text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
                disabled={isPending}
              >
                {preset}
              </button>
            ))}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isPending}>
            Batal
          </Button>
          <Button
            variant={action === 'close' ? 'destructive' : 'default'}
            onClick={handleConfirm}
            disabled={isPending}
          >
            {isPending
              ? 'Memproses...'
              : action === 'open'
                ? 'Buka Katup'
                : 'Tutup Katup'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
