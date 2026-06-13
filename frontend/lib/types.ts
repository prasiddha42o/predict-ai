// Mirrors backend/app/schemas.py. Kept hand-written rather than generated --
// small enough surface that a generator would be more ceremony than value.

export type MachineType = "milling" | "turbofan";
export type HealthStatus = "normal" | "warning" | "critical";
export type AlertSeverity = "warning" | "critical";
export type AlertKind = "failure_probability" | "anomaly_score" | "rul";

export interface Machine {
  id: number;
  name: string;
  machine_type: MachineType;
  quality_type: string | null;
  created_at: string;
}

export interface MachineSummary extends Machine {
  latest_status: HealthStatus | null;
  latest_failure_probability: number | null;
  latest_anomaly_score: number | null;
  latest_rul_cycles: number | null;
  latest_prediction_ts: string | null;
}

export interface FailureDriver {
  feature: string;
  shap_value: number;
  pct: number;
}

export interface PredictionExplanation {
  failure_drivers?: FailureDriver[];
  anomaly_signals?: string[];
  isoforest_score?: number;
  isoforest_threshold?: number;
  autoencoder_score?: number;
  autoencoder_threshold?: number;
  window_cycles?: number;
  rul_cap?: number;
  note?: string | null;
}

export interface Prediction {
  id: number;
  machine_id: number;
  ts: string;
  failure_probability: number | null;
  anomaly_score: number | null;
  rul_cycles: number | null;
  status: HealthStatus;
  explanation: PredictionExplanation | null;
}

export interface Reading {
  id: number;
  machine_id: number;
  ts: string;
  cycle: number | null;
  payload: Record<string, number | string>;
}

export interface Alert {
  id: number;
  machine_id: number;
  ts: string;
  severity: AlertSeverity;
  kind: AlertKind;
  message: string;
  recommended_action: string;
  acknowledged: boolean;
}

export interface MaintenanceRecord {
  id: number;
  machine_id: number;
  maintenance_date: string;
  issue: string;
  action_taken: string;
  parts_replaced: string | null;
  technician: string;
  cost: number;
  created_at: string;
}

export interface MaintenanceRecordInput {
  machine_id: number;
  maintenance_date: string;
  issue: string;
  action_taken: string;
  parts_replaced?: string | null;
  technician: string;
  cost: number;
}

// Shape broadcast on /ws/live -- see backend/app/ws.py's simulator_loop.
export interface LiveTick {
  machine_id: number;
  machine_name: string;
  machine_type: MachineType;
  reading: Record<string, number | string>;
  prediction: {
    failure_probability: number | null;
    anomaly_score: number | null;
    rul_cycles: number | null;
    status: HealthStatus;
    ts: string;
  };
}
