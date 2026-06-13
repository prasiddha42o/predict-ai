// Thin REST client. Every function is a one-line fetch wrapper -- no
// generated SDK, no query-caching library, since the dashboard's real-time
// truth comes from the WebSocket (see useLiveFeed) and REST is only used for
// the initial load and for user-initiated writes (acknowledge, maintenance).

import type {
  Alert,
  MachineSummary,
  MaintenanceRecord,
  MaintenanceRecordInput,
  Prediction,
  Reading,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${init?.method ?? "GET"} ${path} -> ${res.status}: ${body}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  listMachines: () => request<MachineSummary[]>("/machines"),
  getMachine: (id: number) => request<MachineSummary>(`/machines/${id}`),
  getMachineReadings: (id: number, limit = 100) =>
    request<Reading[]>(`/machines/${id}/readings?limit=${limit}`),
  getMachinePredictions: (id: number, limit = 100) =>
    request<Prediction[]>(`/machines/${id}/predictions?limit=${limit}`),

  listAlerts: (unacknowledgedOnly = false) =>
    request<Alert[]>(`/alerts${unacknowledgedOnly ? "?unacknowledged_only=true" : ""}`),
  acknowledgeAlert: (id: number) =>
    request<Alert>(`/alerts/${id}/acknowledge`, { method: "POST" }),

  listMaintenance: (machineId?: number) =>
    request<MaintenanceRecord[]>(
      `/maintenance${machineId != null ? `?machine_id=${machineId}` : ""}`
    ),
  createMaintenance: (payload: MaintenanceRecordInput) =>
    request<MaintenanceRecord>("/maintenance", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  deleteMaintenance: (id: number) =>
    request<void>(`/maintenance/${id}`, { method: "DELETE" }),
};

export const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ?? BASE_URL.replace(/^http/, "ws") + "/ws/live";
