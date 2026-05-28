import axios from 'axios'
import type {
  SensorReading,
  ValveState,
  ValveOverrideLog,
  PredictionResult,
  DashboardSummary,
  ValveID,
  ValveCommandPayload,
  HealthStatus,
} from '@/types'

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 10_000,
})

// Sensors
export const sensorsApi = {
  latest: () =>
    api.get<SensorReading>('/sensors/latest').then((r) => r.data),

  history: (hours = 24) =>
    api
      .get<SensorReading[]>('/sensors/history', { params: { hours } })
      .then((r) => r.data),

  anomalies: (hours = 72) =>
    api
      .get<SensorReading[]>('/sensors/anomalies', { params: { hours } })
      .then((r) => r.data),
}

// Valves
export const valvesApi = {
  list: () =>
    api.get<ValveState[]>('/valves/').then((r) => r.data),

  get: (valveId: ValveID) =>
    api.get<ValveState>(`/valves/${valveId}`).then((r) => r.data),

  command: (valveId: ValveID, payload: ValveCommandPayload) =>
    api.post<ValveState>(`/valves/${valveId}/command`, payload).then((r) => r.data),

  overrides: (valveId: ValveID) =>
    api
      .get<ValveOverrideLog[]>(`/valves/${valveId}/overrides`)
      .then((r) => r.data),

  allOverrides: () =>
    api.get<ValveOverrideLog[]>('/valves/overrides/all').then((r) => r.data),
}

// Predictions
export const predictionsApi = {
  latest: () =>
    api.get<PredictionResult[]>('/predictions/latest').then((r) => r.data),

  run: (hours = 72) =>
    api
      .get<PredictionResult>('/predictions/run', { params: { hours } })
      .then((r) => r.data),
}

// Dashboard
export const dashboardApi = {
  summary: () =>
    api.get<DashboardSummary>('/dashboard/summary').then((r) => r.data),
}

// Health
export const healthApi = {
  check: () =>
    api.get<HealthStatus>('/health').then((r) => r.data),
}

export default api
