'use client'

import { useMutation } from '@tanstack/react-query'
import { useLatestPredictions, useDashboardSummary } from '@/hooks/useSensorData'
import { predictionsApi } from '@/lib/api'
import ETACard from '@/components/predictions/ETACard'
import TrendChart from '@/components/predictions/TrendChart'
import { Button } from '@/components/ui/button'
import { format, parseISO } from 'date-fns'
import { id as idLocale } from 'date-fns/locale'

export default function PredictionsPage() {
  const { data: predictions, isLoading, refetch } = useLatestPredictions()
  const { data: dashboard } = useDashboardSummary()
  const latest = predictions?.[0] ?? null

  const { mutate: runPrediction, isPending } = useMutation({
    mutationFn: () => predictionsApi.run(),
    onSuccess: () => { refetch() },
  })

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Prediksi</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Estimasi waktu degradasi kualitas air</p>
        </div>
        <Button
          onClick={() => runPrediction()}
          disabled={isPending}
          variant="outline"
          size="sm"
        >
          {isPending ? 'Memproses...' : 'Jalankan Prediksi'}
        </Button>
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        <ETACard prediction={latest} isLoading={isLoading} />
        <TrendChart
          data={dashboard?.trend_24h ?? []}
          title="Tren Skor 24 Jam Terakhir"
        />
      </div>

      {(predictions?.length ?? 0) > 0 && (
        <section>
          <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-widest mb-3">
            Riwayat Prediksi
          </h2>
          <div
            className="rounded-xl border border-border bg-card overflow-hidden"
            style={{ boxShadow: '0 2px 12px -4px oklch(0.4 0.1 220 / 0.08)' }}
          >
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-muted/50 text-muted-foreground text-left">
                    <th className="px-4 py-3 font-medium">Dihitung</th>
                    <th className="px-4 py-3 font-medium">Hari Tersisa</th>
                    <th className="px-4 py-3 font-medium">Prediksi Tanggal</th>
                    <th className="px-4 py-3 font-medium">Kepercayaan</th>
                    <th className="px-4 py-3 font-medium">Model</th>
                    <th className="px-4 py-3 font-medium">Notifikasi</th>
                  </tr>
                </thead>
                <tbody>
                  {(predictions ?? []).slice(0, 20).map((p) => (
                    <tr
                      key={p.id}
                      className="border-b border-border/60 last:border-0 hover:bg-muted/40 transition-colors"
                    >
                      <td className="px-4 py-2 text-muted-foreground whitespace-nowrap text-xs font-mono">
                        {format(parseISO(p.computed_at), 'dd MMM yyyy HH:mm', { locale: idLocale })}
                      </td>
                      <td className="px-4 py-2 font-mono tabular-nums">
                        {p.days_until_threshold !== null ? p.days_until_threshold.toFixed(1) : '—'}
                      </td>
                      <td className="px-4 py-2">
                        {p.predicted_date
                          ? format(parseISO(p.predicted_date), 'dd MMM yyyy', { locale: idLocale })
                          : '—'}
                      </td>
                      <td className="px-4 py-2 font-mono tabular-nums">
                        {p.confidence !== null ? `${(p.confidence * 100).toFixed(0)}%` : '—'}
                      </td>
                      <td className="px-4 py-2 text-muted-foreground font-mono">{p.model_used}</td>
                      <td className="px-4 py-2">
                        <span
                          className={
                            p.notification_sent
                              ? 'text-xs text-emerald-600 dark:text-emerald-400'
                              : 'text-xs text-muted-foreground'
                          }
                        >
                          {p.notification_sent ? 'Terkirim' : '—'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}
    </div>
  )
}
