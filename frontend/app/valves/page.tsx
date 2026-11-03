'use client'

import { useValveList, useValveOverrides } from '@/hooks/useSensorData'
import { useWSStore } from '@/hooks/useSensorWebSocket'
import ValveCard from '@/components/valves/ValveCard'
import { Button } from '@/components/ui/button'
import { format } from 'date-fns'
import { id as idLocale } from 'date-fns/locale'
import { cn, toUtcDate } from '@/lib/utils'

export default function ValvesPage() {
  const { data: valves, isLoading, isError, refetch } = useValveList()
  const { data: overrides } = useValveOverrides()
  const liveValveStates = useWSStore((s) => s.valveStates)

  const mergedValves = (valves ?? []).map((valve) => {
    const live = liveValveStates[valve.id]
    return live ? { ...valve, is_open: live.is_open } : valve
  })
  const openCount = mergedValves.filter((v) => v.is_open).length
  const closedCount = mergedValves.length - openCount

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Kontrol Katup</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Kelola status buka/tutup katup solenoid secara manual</p>
      </div>

      {isError ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50/60 p-4 text-sm text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200">
          <p>Gagal memuat status katup. Periksa koneksi ke server.</p>
          <Button variant="outline" size="sm" className="mt-3" onClick={() => refetch()}>
            Coba lagi
          </Button>
        </div>
      ) : isLoading ? (
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-40 rounded-xl border border-border bg-card animate-pulse" />
          ))}
        </div>
      ) : mergedValves.length === 0 ? (
        <div className="rounded-xl border border-border bg-card p-6 text-center">
          <p className="text-sm text-muted-foreground">Belum ada katup terdaftar.</p>
        </div>
      ) : (
        <>
          <div className="flex divide-x divide-border rounded-xl border border-border bg-card">
            {[
              { label: 'Terbuka', value: openCount, className: 'text-emerald-600 dark:text-emerald-400' },
              { label: 'Tertutup', value: closedCount, className: 'text-rose-600 dark:text-rose-400' },
              { label: 'Total Katup', value: mergedValves.length, className: 'text-foreground' },
            ].map(({ label, value, className }) => (
              <div key={label} className="flex-1 px-3 py-3 text-center">
                <p className="text-xs text-muted-foreground">{label}</p>
                <p className={cn('mt-0.5 text-lg font-semibold font-mono tabular-nums', className)}>{value}</p>
              </div>
            ))}
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {mergedValves.map((valve) => (
              <ValveCard key={valve.id} valve={valve} />
            ))}
          </div>
        </>
      )}

      <section>
        <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-widest mb-3">
          Riwayat Override Manual
        </h2>

        {(overrides?.length ?? 0) === 0 ? (
          <div className="rounded-xl border border-dashed border-border bg-card px-4 py-8 text-center">
            <p className="text-sm text-muted-foreground">Belum ada riwayat override.</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Setiap buka/tutup manual akan tercatat di sini.
            </p>
          </div>
        ) : (
          <div
            className="rounded-xl border border-border bg-card overflow-hidden"
            style={{ boxShadow: '0 2px 12px -4px oklch(0.4 0.1 220 / 0.08)' }}
          >
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-muted/50 text-muted-foreground text-left">
                    <th className="px-3 py-3 sm:px-4 font-medium">Waktu</th>
                    <th className="px-3 py-3 sm:px-4 font-medium">Katup</th>
                    <th className="px-3 py-3 sm:px-4 font-medium">Aksi</th>
                    <th className="hidden md:table-cell px-4 py-3 font-medium">Alasan</th>
                    <th className="hidden sm:table-cell px-4 py-3 font-medium">Skor saat Override</th>
                  </tr>
                </thead>
                <tbody>
                  {(overrides ?? []).slice(0, 30).map((log) => (
                    <tr
                      key={log.id}
                      className="border-b border-border/60 last:border-0 hover:bg-muted/40 transition-colors"
                    >
                      <td className="px-3 py-2 sm:px-4 text-muted-foreground whitespace-nowrap text-xs font-mono">
                        {(() => {
                          const d = toUtcDate(log.overridden_at)
                          return d ? format(d, 'dd MMM yyyy HH:mm', { locale: idLocale }) : log.overridden_at
                        })()}
                      </td>
                      <td className="px-3 py-2 sm:px-4 capitalize">{log.valve_id}</td>
                      <td className="px-3 py-2 sm:px-4">
                        <span
                          className={cn(
                            'text-xs font-medium px-2 py-0.5 rounded-full',
                            log.action === 'open'
                              ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300'
                              : 'bg-rose-100 text-rose-700 dark:bg-rose-950/50 dark:text-rose-300',
                          )}
                        >
                          {log.action === 'open' ? 'Buka' : 'Tutup'}
                        </span>
                      </td>
                      <td className="hidden md:table-cell px-4 py-2 text-muted-foreground">{log.reason ?? '—'}</td>
                      <td className="hidden sm:table-cell px-4 py-2 text-muted-foreground font-mono tabular-nums">
                        {log.score_at_override !== null ? log.score_at_override.toFixed(1) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>
    </div>
  )
}
