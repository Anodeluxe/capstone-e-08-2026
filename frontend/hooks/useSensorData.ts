'use client'

import { useQuery } from '@tanstack/react-query'
import { sensorsApi, dashboardApi, predictionsApi, valvesApi } from '@/lib/api'
import {
  mockSensorReadings,
  mockLatestReading,
  mockDashboardSummary,
  mockValveStates,
  mockOverrideLogs,
  mockPredictions,
} from '@/lib/mockData'
import type { ValveID } from '@/types'

const IS_DEMO = process.env.NEXT_PUBLIC_DEMO_MODE === 'true'

export function useLatestSensor() {
  return useQuery({
    queryKey: ['sensors', 'latest'],
    queryFn: sensorsApi.latest,
    refetchInterval: IS_DEMO ? false : 15_000,
    enabled: !IS_DEMO,
    initialData: IS_DEMO ? mockLatestReading : undefined,
  })
}

export function useSensorHistory(hours = 24) {
  return useQuery({
    queryKey: ['sensors', 'history', hours],
    queryFn: () => sensorsApi.history(hours),
    refetchInterval: IS_DEMO ? false : 60_000,
    enabled: !IS_DEMO,
    initialData: IS_DEMO ? mockSensorReadings : undefined,
  })
}

export function useSensorAnomalies(hours = 72) {
  return useQuery({
    queryKey: ['sensors', 'anomalies', hours],
    queryFn: () => sensorsApi.anomalies(hours),
    enabled: !IS_DEMO,
    initialData: IS_DEMO
      ? mockSensorReadings.filter((r) => r.is_sudden_change)
      : undefined,
  })
}

export function useDashboardSummary() {
  return useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: dashboardApi.summary,
    refetchInterval: IS_DEMO ? false : 30_000,
    enabled: !IS_DEMO,
    initialData: IS_DEMO ? mockDashboardSummary : undefined,
  })
}

export function useValveList() {
  return useQuery({
    queryKey: ['valves'],
    queryFn: valvesApi.list,
    enabled: !IS_DEMO,
    initialData: IS_DEMO ? mockValveStates : undefined,
  })
}

export function useValveOverrides(valveId?: ValveID) {
  return useQuery({
    queryKey: ['valves', 'overrides', valveId ?? 'all'],
    queryFn: valveId
      ? () => valvesApi.overrides(valveId)
      : valvesApi.allOverrides,
    enabled: !IS_DEMO,
    initialData: IS_DEMO
      ? valveId
        ? mockOverrideLogs.filter((l) => l.valve_id === valveId)
        : mockOverrideLogs
      : undefined,
  })
}

export function useLatestPredictions() {
  return useQuery({
    queryKey: ['predictions', 'latest'],
    queryFn: predictionsApi.latest,
    refetchInterval: IS_DEMO ? false : 300_000,
    enabled: !IS_DEMO,
    initialData: IS_DEMO ? mockPredictions : undefined,
  })
}
