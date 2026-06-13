"use client";

import type { Alert, AlertSeverity } from "@/lib/types";

const SEVERITY_CONFIG: Record<AlertSeverity, { icon: string; dot: string }> = {
  warning: { icon: "▲", dot: "bg-status-warning" },
  critical: { icon: "■", dot: "bg-status-critical" },
};

export function AlertsPanel({
  alerts,
  onAcknowledge,
}: {
  alerts: Alert[];
  onAcknowledge: (id: number) => void;
}) {
  if (alerts.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-surface p-4 text-sm text-ink-muted">
        No active alerts.
      </div>
    );
  }

  return (
    <ul className="flex flex-col gap-2">
      {alerts.map((alert) => {
        const cfg = SEVERITY_CONFIG[alert.severity];
        return (
          <li
            key={alert.id}
            className="flex items-start gap-3 rounded-lg border border-border bg-surface p-3"
          >
            <span className={`mt-1 h-2 w-2 shrink-0 rounded-full ${cfg.dot}`} aria-hidden />
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium uppercase tracking-wide text-ink-muted">
                  {cfg.icon} {alert.severity}
                </span>
                <span className="text-xs text-ink-muted">
                  {new Date(alert.ts).toLocaleString()}
                </span>
              </div>
              <p className="mt-0.5 text-sm text-foreground">{alert.message}</p>
              <p className="mt-0.5 text-sm text-ink-secondary">
                Recommended action: {alert.recommended_action}
              </p>
            </div>
            {!alert.acknowledged && (
              <button
                onClick={() => onAcknowledge(alert.id)}
                className="shrink-0 rounded-md border border-border px-2.5 py-1 text-xs font-medium text-foreground hover:bg-background"
              >
                Acknowledge
              </button>
            )}
          </li>
        );
      })}
    </ul>
  );
}
