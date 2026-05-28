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
        <h1 className="text-xl font-semibold">Kontrol Katup</h1>
        <p className="text-sm text-zinc-500 mt-0.5">Kelola status buka/tutup katup solenoid secara manual</p>
      </div>

      {isLoading ? (
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-36 rounded-xl border bg-white dark:bg-zinc-900 animate-pulse" />
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
        <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-widest mb-3">
          Riwayat Override Manual
        </h2>

        {(overrides?.length ?? 0) === 0 ? (
          <p className="text-sm text-zinc-400">Belum ada riwayat override.</p>
        ) : (
          <div className="rounded-xl border bg-white dark:bg-zinc-900 overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-zinc-50 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400 text-left">
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
                      className="border-b last:border-0 hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors"
                    >
                      <td className="px-4 py-2 text-zinc-400 whitespace-nowrap text-xs">
                        {format(parseISO(log.overridden_at), 'dd MMM yyyy HH:mm', { locale: idLocale })}
                      </td>
                      <td className="px-4 py-2 capitalize">{log.valve_id}</td>
                      <td className="px-4 py-2">
                        <span
                          className={cn(
                            'text-xs font-medium px-2 py-0.5 rounded-full',
                            log.action === 'open'
                              ? 'bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300'
                              : 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300',
                          )}
                        >
                          {log.action === 'open' ? 'Buka' : 'Tutup'}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-zinc-500">{log.reason ?? '—'}</td>
                      <td className="px-4 py-2 text-zinc-500">
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
