"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { MachineSummary, MaintenanceRecord, MaintenanceRecordInput } from "@/lib/types";
import { MaintenanceForm } from "@/components/MaintenanceForm";

export default function MaintenancePage() {
  const [machines, setMachines] = useState<MachineSummary[]>([]);
  const [records, setRecords] = useState<MaintenanceRecord[]>([]);
  const [error, setError] = useState<string | null>(null);

  function refresh() {
    api.listMaintenance().then(setRecords).catch((err) => setError(String(err)));
  }

  useEffect(() => {
    api.listMachines().then(setMachines).catch(() => {});
    refresh();
  }, []);

  async function handleCreate(payload: MaintenanceRecordInput) {
    await api.createMaintenance(payload);
    refresh();
  }

  async function handleDelete(id: number) {
    await api.deleteMaintenance(id);
    refresh();
  }

  const machineName = (id: number) => machines.find((m) => m.id === id)?.name ?? `Machine #${id}`;

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-6 p-6">
      <Link href="/" className="text-sm text-series-1 hover:underline">
        ← Fleet
      </Link>

      <header>
        <h1 className="text-xl font-semibold">Maintenance history</h1>
        <p className="text-sm text-ink-muted">
          Technician-recorded ground truth: what was actually done, and at what cost.
        </p>
      </header>

      {machines.length > 0 && <MaintenanceForm machines={machines} onSubmit={handleCreate} />}

      {error && <p className="text-sm text-status-critical">{error}</p>}

      <div className="overflow-x-auto rounded-lg border border-border bg-surface">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-ink-muted">
              <th className="px-3 py-2 font-medium">Date</th>
              <th className="px-3 py-2 font-medium">Machine</th>
              <th className="px-3 py-2 font-medium">Issue</th>
              <th className="px-3 py-2 font-medium">Action taken</th>
              <th className="px-3 py-2 font-medium">Technician</th>
              <th className="px-3 py-2 text-right font-medium">Cost</th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody>
            {records.map((r) => (
              <tr key={r.id} className="border-b border-border last:border-0">
                <td className="px-3 py-2 whitespace-nowrap tabular-nums">{r.maintenance_date}</td>
                <td className="px-3 py-2">{machineName(r.machine_id)}</td>
                <td className="px-3 py-2">{r.issue}</td>
                <td className="px-3 py-2">{r.action_taken}</td>
                <td className="px-3 py-2">{r.technician}</td>
                <td className="px-3 py-2 text-right tabular-nums">${r.cost.toFixed(2)}</td>
                <td className="px-3 py-2 text-right">
                  <button
                    onClick={() => handleDelete(r.id)}
                    className="text-xs text-ink-muted hover:text-status-critical"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {records.length === 0 && (
          <p className="p-4 text-sm text-ink-muted">No maintenance records yet.</p>
        )}
      </div>
    </main>
  );
}
