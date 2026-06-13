"use client";

import { useState } from "react";
import type { MachineSummary, MaintenanceRecordInput } from "@/lib/types";

export function MaintenanceForm({
  machines,
  onSubmit,
}: {
  machines: MachineSummary[];
  onSubmit: (payload: MaintenanceRecordInput) => Promise<void>;
}) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    const form = new FormData(e.currentTarget);
    const payload: MaintenanceRecordInput = {
      machine_id: Number(form.get("machine_id")),
      maintenance_date: String(form.get("maintenance_date")),
      issue: String(form.get("issue")),
      action_taken: String(form.get("action_taken")),
      parts_replaced: (form.get("parts_replaced") as string) || null,
      technician: String(form.get("technician")),
      cost: Number(form.get("cost")),
    };
    setSubmitting(true);
    try {
      await onSubmit(payload);
      e.currentTarget.reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save record.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="grid grid-cols-1 gap-3 rounded-lg border border-border bg-surface p-4 sm:grid-cols-2"
    >
      <label className="flex flex-col gap-1 text-sm">
        Machine
        <select name="machine_id" required className="rounded-md border border-border bg-background px-2 py-1.5">
          {machines.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name}
            </option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-1 text-sm">
        Maintenance date
        <input
          type="date"
          name="maintenance_date"
          required
          className="rounded-md border border-border bg-background px-2 py-1.5"
        />
      </label>

      <label className="flex flex-col gap-1 text-sm sm:col-span-2">
        Issue
        <input
          type="text"
          name="issue"
          required
          placeholder="e.g. Excess tool wear"
          className="rounded-md border border-border bg-background px-2 py-1.5"
        />
      </label>

      <label className="flex flex-col gap-1 text-sm sm:col-span-2">
        Action taken
        <input
          type="text"
          name="action_taken"
          required
          placeholder="e.g. Replaced tool"
          className="rounded-md border border-border bg-background px-2 py-1.5"
        />
      </label>

      <label className="flex flex-col gap-1 text-sm">
        Parts replaced
        <input
          type="text"
          name="parts_replaced"
          placeholder="optional"
          className="rounded-md border border-border bg-background px-2 py-1.5"
        />
      </label>

      <label className="flex flex-col gap-1 text-sm">
        Technician
        <input
          type="text"
          name="technician"
          required
          className="rounded-md border border-border bg-background px-2 py-1.5"
        />
      </label>

      <label className="flex flex-col gap-1 text-sm">
        Cost
        <input
          type="number"
          name="cost"
          step="0.01"
          min="0"
          required
          className="rounded-md border border-border bg-background px-2 py-1.5"
        />
      </label>

      <div className="flex items-end sm:col-span-1">
        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-series-1 px-4 py-1.5 text-sm font-medium text-white disabled:opacity-50"
        >
          {submitting ? "Saving..." : "Log maintenance"}
        </button>
      </div>

      {error && <p className="text-sm text-status-critical sm:col-span-2">{error}</p>}
    </form>
  );
}
