'use client'

import { useMutation } from '@tanstack/react-query'
import { useLatestPredictions, useDashboardSummary } from '@/hooks/useSensorData'
import { predictionsApi } from '@/lib/api'
import ETACard from '@/components/predictions/ETACard'
import TrendChart from '@/components/predictions/TrendChart'
import { Button } from '@/components/ui/button'
import { format } from 'date-fns'
import { id as idLocale } from 'date-fns/locale'
import { isStatisticalModel, toUtcDate } from '@/lib/utils'

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
          <h1 className="text-xl font-semibold tracking-tight">Prediksi Degradasi</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Model hybrid memprediksi kapan kualitas air akan melanggar ambang batas
          </p>
        </div>
        <Button
          onClick={() => runPrediction()}
          disabled={isPending}
          variant="outline"
          size="sm"
        >
          {isPending ? 'Menghitung...' : 'Jalankan Model'}
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
        <div className="md:col-span-1">
          <ETACard prediction={latest} isLoading={isLoading} />
        </div>
        <div className="md:col-span-2">
          <TrendChart
            data={dashboard?.trend_24h ?? []}
            title="Tren Kualitas Air (Input Model)"
          />
        </div>
      </div>

      {predictions && predictions.length > 0 && (
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
                    <th className="px-4 py-3 font-medium">Dihitung Pada</th>
                    <th className="px-4 py-3 font-medium">Sisa Waktu</th>
                    <th className="px-4 py-3 font-medium">Perkiraan Tanggal</th>
                    <th className="px-4 py-3 font-medium">Kepercayaan</th>
                    <th className="px-4 py-3 font-medium">Model</th>
                    <th className="px-4 py-3 font-medium">Notifikasi</th>
                  </tr>
                </thead>
                <tbody>
                  {(predictions ?? []).slice(0, 20).map((p) => {
                    const isStat = isStatisticalModel(p.model_used)
                    return (
                      <tr
                        key={p.id}
                        className="border-b border-border/60 last:border-0 hover:bg-muted/40 transition-colors"
                      >
                        <td className="px-4 py-2 text-muted-foreground whitespace-nowrap text-xs font-mono">
                          {(() => {
                            const d = toUtcDate(p.computed_at)
                            return d ? format(d, 'dd MMM yyyy HH:mm', { locale: idLocale }) : p.computed_at
                          })()}
                        </td>
                        <td className="px-4 py-2 font-mono tabular-nums">
                          {p.days_until_threshold !== null ? (
                            p.days_until_threshold.toFixed(1)
                          ) : (
                            <span className="text-xs text-amber-600 dark:text-amber-400 font-sans font-medium">
                              Kekurangan data
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-2">
                          {p.predicted_date
                            ? (() => {
                                const d = toUtcDate(p.predicted_date)
                                return d ? format(d, 'dd MMM yyyy', { locale: idLocale }) : p.predicted_date
                              })()
                            : '—'}
                        </td>
                        <td className="px-4 py-2 font-mono tabular-nums">
                          {!isStat && p.confidence !== null ? `${(p.confidence * 100).toFixed(0)}%` : '—'}
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
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}
    </div>
  )
}
