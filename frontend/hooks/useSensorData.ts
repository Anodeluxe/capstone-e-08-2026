'use client'

import { useQuery } from '@tanstack/react-query'
import { sensorsApi, dashboardApi, predictionsApi, valvesApi } from '@/lib/api'
import type { ValveID } from '@/types'

export function useLatestSensor() {
  return useQuery({
    queryKey: ['sensors', 'latest'],
    queryFn: sensorsApi.latest,
    refetchInterval: 15_000,
  })
}

export function useSensorHistory(hours = 24) {
  return useQuery({
    queryKey: ['sensors', 'history', hours],
    queryFn: () => sensorsApi.history(hours),
    refetchInterval: 60_000,
  })
}

export function useSensorAnomalies(hours = 72) {
  return useQuery({
    queryKey: ['sensors', 'anomalies', hours],
    queryFn: () => sensorsApi.anomalies(hours),
  })
}

export function useDashboardSummary() {
  return useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: dashboardApi.summary,
    refetchInterval: 30_000,
  })
}

export function useValveList() {
  return useQuery({
    queryKey: ['valves'],
    queryFn: valvesApi.list,
  })
}

export function useValveOverrides(valveId?: ValveID) {
  return useQuery({
    queryKey: ['valves', 'overrides', valveId ?? 'all'],
    queryFn: valveId
      ? () => valvesApi.overrides(valveId)
      : valvesApi.allOverrides,
  })
}

export function useLatestPredictions() {
  return useQuery({
    queryKey: ['predictions', 'latest'],
    queryFn: predictionsApi.latest,
    refetchInterval: 300_000,
  })
}
