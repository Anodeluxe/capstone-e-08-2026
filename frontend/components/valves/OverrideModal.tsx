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
          <div className="rounded-md bg-yellow-50 dark:bg-yellow-950 border border-yellow-200 dark:border-yellow-800 px-3 py-2 text-sm text-yellow-800 dark:text-yellow-200">
            Menutup katup secara manual dapat mempengaruhi distribusi air ke{' '}
            {VALVE_LABELS[valve.id].toLowerCase()}.
          </div>
        )}

        <div>
          <label className="text-sm font-medium mb-1.5 block">
            Alasan <span className="text-zinc-400 font-normal">(opsional)</span>
          </label>
          <input
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !isPending && handleConfirm()}
            placeholder="Masukkan alasan override..."
            className="w-full rounded-md border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-zinc-400 dark:bg-zinc-800 dark:border-zinc-700"
            disabled={isPending}
          />
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
