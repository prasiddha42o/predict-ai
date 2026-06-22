"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { MachineSummary, Prediction, Reading } from "@/lib/types";
import { useLiveFeed } from "@/lib/useLiveFeed";
import { HealthBadge } from "@/components/HealthBadge";
import { StatTile } from "@/components/StatTile";
import { SensorChart } from "@/components/SensorChart";

// Which raw payload fields to chart per machine type, and how to label them.
// Milling: the five AI4I sensors. Turbofan: three representative C-MAPSS
// sensors (temperature-like channels) -- charting all 17 model features
// would be noise, not signal, on a detail page.
const MILLING_CHARTS: { key: string; title: string; unit: string }[] = [
  { key: "process_temp_k", title: "Process temperature", unit: "K" },
  { key: "torque_nm", title: "Torque", unit: "Nm" },
  { key: "tool_wear_min", title: "Tool wear", unit: "min" },
];

const TURBOFAN_CHARTS: { key: string; title: string; unit: string }[] = [
  { key: "sensor_2", title: "Sensor 2 (temperature)", unit: "" },
  { key: "sensor_3", title: "Sensor 3 (temperature)", unit: "" },
  { key: "sensor_4", title: "Sensor 4 (temperature)", unit: "" },
];

export function MachineDetail({ id }: { id: number }) {
  const [machine, setMachine] = useState<MachineSummary | null>(null);
  const [readings, setReadings] = useState<Reading[]>([]);
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [error, setError] = useState<string | null>(null);
  const { ticksByMachine } = useLiveFeed();

  useEffect(() => {
    Promise.all([api.getMachine(id), api.getMachineReadings(id), api.getMachinePredictions(id)])
      .then(([m, r, p]) => {
        setMachine(m);
        setReadings(r);
        setPredictions(p);
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, [id]);

  const tick = ticksByMachine[id];
  useEffect(() => {
    if (!tick) return;
    setReadings((prev) => [
      ...prev,
      { id: -Date.now(), machine_id: id, ts: tick.prediction.ts, cycle: null, payload: tick.reading },
    ]);
    setPredictions((prev) => [
      ...prev,
      {
        id: -Date.now(),
        machine_id: id,
        ts: tick.prediction.ts,
        failure_probability: tick.prediction.failure_probability,
        anomaly_score: tick.prediction.anomaly_score,
        rul_cycles: tick.prediction.rul_cycles,
        status: tick.prediction.status,
        explanation: null,
      },
    ]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tick]);

  const latest = predictions.at(-1) ?? null;
  // `machine` comes from GET /machines/{id} (`MachineOut`), which has no
  // status field -- that only exists on the list endpoint's `MachineSummary`.
  // The real status lives on the latest prediction this page already fetched.
  // Left `null` (not defaulted to "normal") when nothing has been scored yet
  // -- HealthBadge renders that as a distinct "Unscored" state.
  const status = tick?.prediction.status ?? latest?.status ?? null;
  const tone = status === "critical" ? "critical" : status === "warning" ? "warning" : "default";

  const chartSpecs = machine?.machine_type === "turbofan" ? TURBOFAN_CHARTS : MILLING_CHARTS;
  const chartData = useMemo(
    () =>
      chartSpecs.map((spec) => ({
        ...spec,
        points: readings
          .filter((r) => typeof r.payload[spec.key] === "number")
          .map((r) => ({
            ts: new Date(r.ts).toLocaleTimeString(),
            value: r.payload[spec.key] as number,
          }))
          .slice(-60),
      })),
    [readings, chartSpecs]
  );

  if (error) {
    return (
      <main className="mx-auto max-w-3xl p-6">
        <p className="rounded-lg border border-status-critical/30 bg-surface p-3 text-sm text-status-critical">
          {error}
        </p>
      </main>
    );
  }

  if (!machine) {
    return <main className="mx-auto max-w-3xl p-6 text-sm text-ink-muted">Loading…</main>;
  }

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-6 p-6">
      <Link href="/" className="text-sm text-series-1 hover:underline">
        ← Fleet
      </Link>

      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">{machine.name}</h1>
          <p className="text-sm text-ink-muted">
            {machine.machine_type === "milling"
              ? `Milling machine · quality type ${machine.quality_type ?? "—"}`
              : "Turbofan engine (NASA C-MAPSS FD001)"}
          </p>
        </div>
        <HealthBadge status={status} />
      </header>

      <div className="grid grid-cols-2 gap-3">
        {machine.machine_type === "milling" ? (
          <>
            <StatTile
              label="Failure probability"
              value={
                latest?.failure_probability != null
                  ? `${(latest.failure_probability * 100).toFixed(0)}%`
                  : "—"
              }
              tone={tone}
            />
            <StatTile
              label="Anomaly score"
              value={latest?.anomaly_score != null ? latest.anomaly_score.toFixed(2) : "—"}
            />
          </>
        ) : (
          <StatTile
            label="Estimated RUL"
            value={latest?.rul_cycles != null ? `${latest.rul_cycles.toFixed(0)} cycles` : "—"}
            tone={tone}
          />
        )}
      </div>

      {latest?.explanation?.failure_drivers && (
        <section className="rounded-lg border border-border bg-surface p-4">
          <h2 className="mb-2 text-sm font-medium text-ink-secondary">Top contributing signals</h2>
          <ul className="flex flex-col gap-1">
            {latest.explanation.failure_drivers.map((d) => (
              <li key={d.feature} className="flex items-center justify-between text-sm">
                <span className="text-foreground">{d.feature}</span>
                <span
                  className={`tabular-nums ${d.pct >= 0 ? "text-status-critical" : "text-status-good"}`}
                >
                  {d.pct >= 0 ? "+" : ""}
                  {d.pct.toFixed(1)}%
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="flex flex-col gap-3">
        <h2 className="text-sm font-medium text-ink-secondary">Sensor trends</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {chartData.map((c) => (
            <SensorChart key={c.key} title={c.title} unit={c.unit} data={c.points} />
          ))}
        </div>
      </section>
    </main>
  );
}
