"use client";

import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface Point {
  ts: string;
  value: number;
}

// Single-series sensor trend -- one axis, thin 2px line, recessive grid/axis,
// hover tooltip. Series identity comes from the title, not from picking a
// color per sensor (a single series needs no legend box).
export function SensorChart({
  title,
  unit,
  data,
  color = "var(--series-1)",
}: {
  title: string;
  unit?: string;
  data: Point[];
  color?: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-surface p-3">
      <div className="mb-1 flex items-baseline justify-between">
        <h3 className="text-sm font-medium text-foreground">{title}</h3>
        {unit && <span className="text-xs text-ink-muted">{unit}</span>}
      </div>
      <div className="h-40">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
            <XAxis
              dataKey="ts"
              tick={{ fontSize: 10, fill: "var(--ink-muted)" }}
              axisLine={{ stroke: "var(--gridline)" }}
              tickLine={false}
              minTickGap={40}
            />
            <YAxis
              tick={{ fontSize: 10, fill: "var(--ink-muted)" }}
              axisLine={false}
              tickLine={false}
              width={40}
              domain={["auto", "auto"]}
            />
            <Tooltip
              contentStyle={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                fontSize: 12,
              }}
              labelStyle={{ color: "var(--ink-secondary)" }}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
