export interface SensorReading {
  id: number
  timestamp: string
  ph: number
  turbidity: number
  tds: number
  temperature: number
  water_level: number
  score_overall: number | null
  score_bathroom: number | null
  score_kitchen: number | null
  score_laundry: number | null
  score_garden: number | null
  is_sudden_change: boolean
  anomaly_parameter: string | null
}

export type ValveID = 'bathroom' | 'kitchen' | 'laundry' | 'garden'

export interface ValveState {
  id: ValveID
  is_open: boolean
  last_changed_at: string
  last_changed_by: string
  quality_score_at_close: number | null
}

export interface ValveOverrideLog {
  id: number
  valve_id: ValveID
  action: 'open' | 'close'
  reason: string | null
  score_at_override: number | null
  overridden_at: string
  user_id: string | null
}

export interface PredictionResult {
  id: number
  computed_at: string
  target_parameter: string
  valve_id: ValveID | null
  days_until_threshold: number | null
  predicted_date: string | null
  confidence: number | null
  model_used: string
  notification_sent: boolean
}

export interface ScoreBreakdown {
  overall: number | null
  bathroom: number | null
  kitchen: number | null
  laundry: number | null
  garden: number | null
}

export interface DashboardSummary {
  latest_reading: SensorReading | null
  valve_states: ValveState[]
  prediction: PredictionResult | null
  trend_24h: Array<{
    hour: string
    avg_score: number | null
    avg_ph: number | null
    avg_turbidity: number | null
    avg_tds: number | null
  }>
  anomaly_count_24h: number
  system_status: {
    mqtt_connected: boolean
    last_reading_age_seconds: number | null
  }
}

export type WSEventType = 'sensor_update' | 'valve_status' | 'alert'

export interface WSEvent {
  type: WSEventType
  data: Record<string, unknown>
}

export interface AlertData {
  alert_type: 'sudden_change' | 'early_warning' | 'valve_closed'
  message: string
  details: Record<string, unknown>
}

export interface ValveCommandPayload {
  action: 'open' | 'close'
  reason?: string
}

export interface HealthStatus {
  mqtt_connected: boolean
  ws_clients: number
  env: string
}
