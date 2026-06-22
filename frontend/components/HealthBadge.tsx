import type { HealthStatus } from "@/lib/types";

// Status colors never carry meaning alone -- icon + label always ship
// together with the color, per the dataviz status-palette rule.
const CONFIG: Record<HealthStatus, { label: string; dot: string; icon: string }> = {
  normal: { label: "Normal", dot: "bg-status-good", icon: "●" },
  warning: { label: "Warning", dot: "bg-status-warning", icon: "▲" },
  critical: { label: "Critical", dot: "bg-status-critical", icon: "■" },
};

export function HealthBadge({ status }: { status: HealthStatus | null }) {
  // `null` means "never scored yet" -- a genuinely different fact from
  // "scored and healthy". Defaulting it to a green "Normal" would assert
  // something we don't actually know, and would silently disagree with the
  // dashboard's own healthy/warning/critical counts, which correctly
  // exclude unscored machines from all three buckets.
  if (status === null) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-border px-2.5 py-1 text-xs font-medium text-ink-muted">
        <span className="h-2 w-2 rounded-full bg-ink-muted" aria-hidden />
        Unscored
      </span>
    );
  }

  const c = CONFIG[status];
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-border px-2.5 py-1 text-xs font-medium">
      <span className={`h-2 w-2 rounded-full ${c.dot}`} aria-hidden />
      {c.label}
    </span>
  );
}
