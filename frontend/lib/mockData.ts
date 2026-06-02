import type {
  SensorReading,
  ValveState,
  ValveOverrideLog,
  PredictionResult,
  DashboardSummary,
  AlertData,
} from '@/types'

// Base timestamp: 2026-06-02T14:00:00 (now), readings go 24h back
const BASE = new Date('2026-06-02T14:00:00+07:00')

function ts(minutesAgo: number): string {
  return new Date(BASE.getTime() - minutesAgo * 60 * 1000).toISOString()
}

// 48 readings, one per 30 min over the last 24 hours
const RAW: Array<{
  min: number
  ph: number
  turb: number
  tds: number
  temp: number
  wl: number
  score: number
  anomaly?: boolean
  anomalyParam?: string
}> = [
  { min: 0,    ph: 7.12, turb: 2.1, tds: 148, temp: 27.8, wl: 72.4, score: 79 },
  { min: 30,   ph: 7.14, turb: 2.0, tds: 147, temp: 27.9, wl: 72.8, score: 80 },
  { min: 60,   ph: 7.10, turb: 2.3, tds: 150, temp: 27.7, wl: 73.1, score: 78 },
  { min: 90,   ph: 7.08, turb: 2.5, tds: 152, temp: 27.6, wl: 73.5, score: 77 },
  { min: 120,  ph: 7.11, turb: 2.2, tds: 149, temp: 27.8, wl: 74.0, score: 79 },
  { min: 150,  ph: 7.09, turb: 2.4, tds: 151, temp: 27.7, wl: 74.3, score: 78 },
  { min: 180,  ph: 7.13, turb: 2.1, tds: 148, temp: 27.9, wl: 74.7, score: 80 },
  { min: 210,  ph: 7.15, turb: 1.9, tds: 146, temp: 28.0, wl: 75.2, score: 81 },
  { min: 240,  ph: 7.16, turb: 1.8, tds: 145, temp: 28.1, wl: 75.5, score: 82 },
  { min: 270,  ph: 7.14, turb: 2.0, tds: 147, temp: 28.0, wl: 75.9, score: 81 },
  { min: 300,  ph: 7.12, turb: 2.2, tds: 149, temp: 27.9, wl: 76.4, score: 79 },
  { min: 330,  ph: 7.10, turb: 2.4, tds: 151, temp: 27.8, wl: 76.8, score: 78 },
  { min: 360,  ph: 7.08, turb: 2.6, tds: 153, temp: 27.7, wl: 77.3, score: 77 },
  { min: 390,  ph: 7.06, turb: 2.8, tds: 155, temp: 27.6, wl: 77.7, score: 75 },
  { min: 420,  ph: 7.05, turb: 3.0, tds: 157, temp: 27.5, wl: 78.1, score: 74 },
  { min: 450,  ph: 7.07, turb: 2.9, tds: 156, temp: 27.6, wl: 78.5, score: 75 },
  { min: 480,  ph: 7.09, turb: 2.7, tds: 154, temp: 27.7, wl: 78.9, score: 76 },
  { min: 510,  ph: 7.11, turb: 2.5, tds: 152, temp: 27.8, wl: 79.4, score: 77 },
  { min: 540,  ph: 7.10, turb: 2.6, tds: 153, temp: 27.7, wl: 79.8, score: 77 },
  { min: 570,  ph: 7.08, turb: 2.8, tds: 155, temp: 27.6, wl: 80.2, score: 75 },
  { min: 600,  ph: 7.07, turb: 3.1, tds: 158, temp: 27.5, wl: 80.6, score: 74 },
  { min: 630,  ph: 7.05, turb: 3.3, tds: 160, temp: 27.4, wl: 81.0, score: 72 },
  { min: 660,  ph: 7.04, turb: 3.5, tds: 162, temp: 27.3, wl: 81.4, score: 71 },
  { min: 690,  ph: 7.02, turb: 3.7, tds: 164, temp: 27.2, wl: 81.8, score: 70 },
  { min: 720,  ph: 7.00, turb: 3.9, tds: 167, temp: 27.1, wl: 82.2, score: 69 },
  { min: 750,  ph: 6.98, turb: 4.1, tds: 169, temp: 27.0, wl: 82.6, score: 67 },
  { min: 780,  ph: 6.96, turb: 4.3, tds: 171, temp: 26.9, wl: 83.0, score: 66 },
  { min: 810,  ph: 6.94, turb: 4.5, tds: 173, temp: 26.8, wl: 83.4, score: 65 },
  // anomaly — pH spike
  { min: 840,  ph: 5.21, turb: 4.8, tds: 178, temp: 26.7, wl: 83.8, score: 38, anomaly: true, anomalyParam: 'ph' },
  { min: 870,  ph: 6.90, turb: 4.6, tds: 175, temp: 26.7, wl: 84.0, score: 65 },
  { min: 900,  ph: 6.92, turb: 4.4, tds: 173, temp: 26.8, wl: 84.3, score: 66 },
  { min: 930,  ph: 6.95, turb: 4.2, tds: 171, temp: 26.9, wl: 84.6, score: 67 },
  { min: 960,  ph: 6.97, turb: 4.0, tds: 169, temp: 27.0, wl: 84.9, score: 68 },
  { min: 990,  ph: 6.99, turb: 3.8, tds: 167, temp: 27.1, wl: 85.2, score: 70 },
  { min: 1020, ph: 7.01, turb: 3.6, tds: 165, temp: 27.2, wl: 85.5, score: 71 },
  { min: 1050, ph: 7.03, turb: 3.4, tds: 163, temp: 27.3, wl: 85.8, score: 72 },
  { min: 1080, ph: 7.05, turb: 3.2, tds: 161, temp: 27.4, wl: 86.1, score: 73 },
  { min: 1110, ph: 7.07, turb: 3.0, tds: 159, temp: 27.5, wl: 86.4, score: 75 },
  { min: 1140, ph: 7.09, turb: 2.8, tds: 157, temp: 27.6, wl: 86.7, score: 76 },
  // second anomaly — TDS spike
  { min: 1170, ph: 7.08, turb: 3.1, tds: 215, temp: 27.5, wl: 87.0, score: 52, anomaly: true, anomalyParam: 'tds' },
  { min: 1200, ph: 7.10, turb: 2.9, tds: 161, temp: 27.6, wl: 87.3, score: 76 },
  { min: 1230, ph: 7.11, turb: 2.7, tds: 159, temp: 27.7, wl: 87.5, score: 77 },
  { min: 1260, ph: 7.13, turb: 2.5, tds: 157, temp: 27.8, wl: 87.7, score: 78 },
  { min: 1290, ph: 7.14, turb: 2.3, tds: 155, temp: 27.9, wl: 87.9, score: 79 },
  { min: 1320, ph: 7.15, turb: 2.1, tds: 153, temp: 28.0, wl: 88.1, score: 80 },
  { min: 1350, ph: 7.16, turb: 2.0, tds: 151, temp: 28.1, wl: 88.3, score: 81 },
  { min: 1380, ph: 7.17, turb: 1.9, tds: 149, temp: 28.2, wl: 88.5, score: 82 },
  { min: 1410, ph: 7.18, turb: 1.8, tds: 148, temp: 28.3, wl: 88.6, score: 82 },
]

export const mockSensorReadings: SensorReading[] = RAW.map((r, i) => ({
  id: 1000 + i,
  timestamp: ts(r.min),
  ph: r.ph,
  turbidity: r.turb,
  tds: r.tds,
  temperature: r.temp,
  water_level: r.wl,
  score_overall: r.score,
  score_bathroom: r.anomaly ? null : Math.min(100, r.score + 2),
  score_kitchen: r.anomaly ? null : Math.min(100, r.score + 6),
  score_laundry: r.anomaly ? null : Math.max(0, r.score - 8),
  score_garden: r.anomaly ? null : Math.max(0, r.score - 4),
  is_sudden_change: r.anomaly ?? false,
  anomaly_parameter: r.anomalyParam ?? null,
}))

// Most recent reading (minutes = 0)
export const mockLatestReading = mockSensorReadings[0]

export const mockValveStates: ValveState[] = [
  {
    id: 'bathroom',
    is_open: true,
    last_changed_at: ts(95),
    last_changed_by: 'system',
    quality_score_at_close: null,
  },
  {
    id: 'kitchen',
    is_open: true,
    last_changed_at: ts(110),
    last_changed_by: 'system',
    quality_score_at_close: null,
  },
  {
    id: 'laundry',
    is_open: false,
    last_changed_at: ts(75),
    last_changed_by: 'manual_override',
    quality_score_at_close: 41.3,
  },
  {
    id: 'garden',
    is_open: true,
    last_changed_at: ts(130),
    last_changed_by: 'system',
    quality_score_at_close: null,
  },
]

export const mockOverrideLogs: ValveOverrideLog[] = [
  {
    id: 201,
    valve_id: 'laundry',
    action: 'close',
    reason: 'Kualitas air di bawah standar laundri',
    score_at_override: 41.3,
    overridden_at: ts(75),
    user_id: 'admin',
  },
  {
    id: 200,
    valve_id: 'garden',
    action: 'open',
    reason: 'Penyiraman taman manual',
    score_at_override: 72.5,
    overridden_at: ts(130),
    user_id: 'admin',
  },
  {
    id: 199,
    valve_id: 'laundry',
    action: 'open',
    reason: 'Test setelah perbaikan sensor',
    score_at_override: 68.0,
    overridden_at: ts(60 * 24 + 45),
    user_id: 'teknisi',
  },
  {
    id: 198,
    valve_id: 'bathroom',
    action: 'close',
    reason: 'Pemeliharaan pipa kamar mandi',
    score_at_override: 76.2,
    overridden_at: ts(60 * 24 * 2 + 30),
    user_id: 'teknisi',
  },
  {
    id: 197,
    valve_id: 'bathroom',
    action: 'open',
    reason: 'Pemeliharaan selesai',
    score_at_override: 79.1,
    overridden_at: ts(60 * 24 * 2 + 15),
    user_id: 'teknisi',
  },
  {
    id: 196,
    valve_id: 'kitchen',
    action: 'close',
    reason: null,
    score_at_override: 58.4,
    overridden_at: ts(60 * 24 * 3 + 20),
    user_id: 'admin',
  },
  {
    id: 195,
    valve_id: 'kitchen',
    action: 'open',
    reason: null,
    score_at_override: 71.0,
    overridden_at: ts(60 * 24 * 3 + 10),
    user_id: 'admin',
  },
  {
    id: 194,
    valve_id: 'garden',
    action: 'close',
    reason: 'Musim hujan, tidak perlu penyiraman',
    score_at_override: 82.3,
    overridden_at: ts(60 * 24 * 5 + 60),
    user_id: 'admin',
  },
]

export const mockPredictions: PredictionResult[] = [
  {
    id: 51,
    computed_at: ts(15),
    target_parameter: 'ph',
    valve_id: 'laundry',
    days_until_threshold: 4.2,
    predicted_date: new Date(BASE.getTime() + 4.2 * 24 * 60 * 60 * 1000).toISOString(),
    confidence: 0.78,
    model_used: 'linear_regression',
    notification_sent: true,
  },
  {
    id: 50,
    computed_at: ts(60 * 6),
    target_parameter: 'ph',
    valve_id: 'laundry',
    days_until_threshold: 5.8,
    predicted_date: new Date(BASE.getTime() + 5.8 * 24 * 60 * 60 * 1000).toISOString(),
    confidence: 0.74,
    model_used: 'linear_regression',
    notification_sent: false,
  },
  {
    id: 49,
    computed_at: ts(60 * 12),
    target_parameter: 'tds',
    valve_id: null,
    days_until_threshold: 7.1,
    predicted_date: new Date(BASE.getTime() + 7.1 * 24 * 60 * 60 * 1000).toISOString(),
    confidence: 0.81,
    model_used: 'linear_regression',
    notification_sent: false,
  },
  {
    id: 48,
    computed_at: ts(60 * 24),
    target_parameter: 'ph',
    valve_id: null,
    days_until_threshold: 9.3,
    predicted_date: new Date(BASE.getTime() + 9.3 * 24 * 60 * 60 * 1000).toISOString(),
    confidence: 0.69,
    model_used: 'moving_average',
    notification_sent: false,
  },
  {
    id: 47,
    computed_at: ts(60 * 48),
    target_parameter: 'turbidity',
    valve_id: null,
    days_until_threshold: 12.6,
    predicted_date: new Date(BASE.getTime() + 12.6 * 24 * 60 * 60 * 1000).toISOString(),
    confidence: 0.65,
    model_used: 'moving_average',
    notification_sent: false,
  },
]

// 24 hourly trend points (last 24h, most recent first reversed to chronological)
const trendPoints = Array.from({ length: 24 }, (_, i) => {
  const minutesAgo = (23 - i) * 60
  const baseScore = 79 - i * 0.4 + Math.sin(i * 0.5) * 3
  return {
    hour: ts(minutesAgo),
    avg_score: parseFloat(Math.max(60, Math.min(84, baseScore)).toFixed(1)),
    avg_ph: parseFloat((7.18 - i * 0.014).toFixed(2)),
    avg_turbidity: parseFloat((1.8 + i * 0.11).toFixed(1)),
    avg_tds: parseFloat((145 + i * 1.8).toFixed(0)),
  }
})

export const mockDashboardSummary: DashboardSummary = {
  latest_reading: mockLatestReading,
  valve_states: mockValveStates,
  prediction: mockPredictions[0],
  trend_24h: trendPoints,
  anomaly_count_24h: 2,
  system_status: {
    mqtt_connected: true,
    last_reading_age_seconds: 18,
  },
}

export const mockAlert: AlertData = {
  alert_type: 'early_warning',
  message: 'Tren pH menunjukkan penurunan bertahap. Prediksi degradasi air dalam 4.2 hari.',
  details: {
    parameter: 'ph',
    current_value: 7.12,
    trend_slope: -0.014,
    days_until_threshold: 4.2,
  },
}
