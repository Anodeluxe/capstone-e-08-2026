'use client'

import { useValveList, useValveOverrides } from '@/hooks/useSensorData'
import ValveCard from '@/components/valves/ValveCard'
import { format, parseISO } from 'date-fns'
import { id as idLocale } from 'date-fns/locale'
import { cn } from '@/lib/utils'

export default function ValvesPage() {
  const { data: valves, isLoading } = useValveList()
  const { data: overrides } = useValveOverrides()

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Kontrol Katup</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Kelola status buka/tutup katup solenoid secara manual</p>
      </div>

      {isLoading ? (
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-36 rounded-xl border border-border bg-card animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {(valves ?? []).map((valve) => (
            <ValveCard key={valve.id} valve={valve} />
          ))}
        </div>
      )}

      <section>
        <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-widest mb-3">
          Riwayat Override Manual
        </h2>

        {(overrides?.length ?? 0) === 0 ? (
          <p className="text-sm text-muted-foreground">Belum ada riwayat override.</p>
        ) : (
          <div
            className="rounded-xl border border-border bg-card overflow-hidden"
            style={{ boxShadow: '0 2px 12px -4px oklch(0.4 0.1 220 / 0.08)' }}
          >
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-muted/50 text-muted-foreground text-left">
                    <th className="px-4 py-3 font-medium">Waktu</th>
                    <th className="px-4 py-3 font-medium">Katup</th>
                    <th className="px-4 py-3 font-medium">Aksi</th>
                    <th className="px-4 py-3 font-medium">Alasan</th>
                    <th className="px-4 py-3 font-medium">Skor saat Override</th>
                  </tr>
                </thead>
                <tbody>
                  {(overrides ?? []).slice(0, 30).map((log) => (
                    <tr
                      key={log.id}
                      className="border-b border-border/60 last:border-0 hover:bg-muted/40 transition-colors"
                    >
                      <td className="px-4 py-2 text-muted-foreground whitespace-nowrap text-xs font-mono">
                        {format(parseISO(log.overridden_at), 'dd MMM yyyy HH:mm', { locale: idLocale })}
                      </td>
                      <td className="px-4 py-2 capitalize">{log.valve_id}</td>
                      <td className="px-4 py-2">
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
                      <td className="px-4 py-2 text-muted-foreground">{log.reason ?? '—'}</td>
                      <td className="px-4 py-2 text-muted-foreground font-mono tabular-nums">
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
