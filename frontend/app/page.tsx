"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { Alert, HealthStatus, MachineSummary } from "@/lib/types";
import { useLiveFeed } from "@/lib/useLiveFeed";
import { AlertsPanel } from "@/components/AlertsPanel";
import { HealthBadge } from "@/components/HealthBadge";
import { StatTile } from "@/components/StatTile";

export default function DashboardPage() {
  const [machines, setMachines] = useState<MachineSummary[] | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [error, setError] = useState<string | null>(null);
  const { ticksByMachine, connected } = useLiveFeed();

  function refreshAlerts() {
    api.listAlerts(true).then(setAlerts).catch(() => {});
  }

  useEffect(() => {
    api
      .listMachines()
      .then(setMachines)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
    refreshAlerts();
    // Alerts are created server-side as a side effect of scoring -- poll
    // rather than push a dedicated WS message for them, since they're
    // low-frequency compared to the sensor tick rate.
    const interval = setInterval(refreshAlerts, 10_000);
    return () => clearInterval(interval);
  }, []);

  async function handleAcknowledge(id: number) {
    await api.acknowledgeAlert(id);
    refreshAlerts();
  }

  // Live ticks overlay the REST snapshot -- same merge the detail page uses.
  const merged = useMemo(() => {
    if (!machines) return null;
    return machines.map((m) => {
      const tick = ticksByMachine[m.id];
      if (!tick) return m;
      return {
        ...m,
        latest_status: tick.prediction.status,
        latest_failure_probability: tick.prediction.failure_probability,
        latest_anomaly_score: tick.prediction.anomaly_score,
        latest_rul_cycles: tick.prediction.rul_cycles,
        latest_prediction_ts: tick.prediction.ts,
      };
    });
  }, [machines, ticksByMachine]);

  const counts = useMemo(() => {
    const base: Record<HealthStatus | "unknown", number> = {
      normal: 0,
      warning: 0,
      critical: 0,
      unknown: 0,
    };
    for (const m of merged ?? []) {
      base[m.latest_status ?? "unknown"] += 1;
    }
    return base;
  }, [merged]);

  return (
    <main className="mx-auto flex max-w-5xl flex-col gap-6 p-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">PredictAI</h1>
          <p className="text-sm text-ink-muted">Machine health & failure risk, fleet-wide.</p>
        </div>
        <span className="flex items-center gap-1.5 text-xs text-ink-muted">
          <span
            className={`h-2 w-2 rounded-full ${connected ? "bg-status-good" : "bg-status-critical"}`}
            aria-hidden
          />
          {connected ? "Live" : "Reconnecting…"}
        </span>
      </header>

      {error && (
        <p className="rounded-lg border border-status-critical/30 bg-surface p-3 text-sm text-status-critical">
          {error}
        </p>
      )}

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="Machines" value={merged?.length ?? "—"} />
        <StatTile label="Healthy" value={counts.normal} tone="good" />
        <StatTile label="Warning" value={counts.warning} tone="warning" />
        <StatTile label="Critical" value={counts.critical} tone="critical" />
      </div>

      <section className="flex flex-col gap-2">
        <h2 className="text-sm font-medium text-ink-secondary">
          Active alerts {alerts.length > 0 && `(${alerts.length})`}
        </h2>
        <AlertsPanel alerts={alerts} onAcknowledge={handleAcknowledge} />
      </section>

      <section className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-medium text-ink-secondary">Fleet</h2>
          <Link href="/maintenance" className="text-sm text-series-1 hover:underline">
            Maintenance history →
          </Link>
        </div>

        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {merged?.map((m) => (
            <Link
              key={m.id}
              href={`/machines/${m.id}`}
              className="flex items-center justify-between rounded-lg border border-border bg-surface p-3 hover:bg-background"
            >
              <div>
                <div className="text-sm font-medium">{m.name}</div>
                <div className="text-xs text-ink-muted">
                  {m.machine_type === "milling"
                    ? `Milling machine · type ${m.quality_type ?? "—"}`
                    : "Turbofan engine"}
                </div>
              </div>
              <div className="flex items-center gap-3">
                {m.machine_type === "milling" && m.latest_failure_probability != null && (
                  <span className="text-sm tabular-nums text-ink-secondary">
                    {(m.latest_failure_probability * 100).toFixed(0)}% risk
                  </span>
                )}
                {m.machine_type === "turbofan" && m.latest_rul_cycles != null && (
                  <span className="text-sm tabular-nums text-ink-secondary">
                    {m.latest_rul_cycles.toFixed(0)} cycles left
                  </span>
                )}
                <HealthBadge status={m.latest_status ?? "normal"} />
              </div>
            </Link>
          ))}
        </div>

        {merged?.length === 0 && (
          <p className="text-sm text-ink-muted">
            No machines yet — run <code>python -m app.seed</code> in the backend.
          </p>
        )}
      </section>
    </main>
  );
}
