"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { colors } from "@/styles/tokens";

export interface ImpactBar {
  metric: string;
  change_pct: number | null;
}

/** Projected % change per metric under the scenario. A horizontal bar makes
 * metrics on very different absolute scales (USD millions vs goal points)
 * directly comparable — each bar is (projected-current)/current from the real
 * snapshot, positive teal / negative red. No invented values. */
export function WhatIfImpactBars({ data }: { data: ImpactBar[] }) {
  const rows = data
    .filter((d) => d.change_pct !== null)
    .map((d) => ({ metric: d.metric, pct: Number(d.change_pct) }));

  return (
    <div className="h-[220px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 44, bottom: 4, left: 8 }}>
          <CartesianGrid horizontal={false} stroke={colors.surface.border} strokeOpacity={0.6} />
          <XAxis
            type="number"
            tickFormatter={(v: number) => `${v > 0 ? "+" : ""}${v.toFixed(0)}%`}
            tick={{ fontSize: 10, fill: colors.text.muted }}
            tickLine={false}
            axisLine={{ stroke: colors.surface.border }}
          />
          <YAxis
            type="category"
            dataKey="metric"
            tick={{ fontSize: 11, fill: colors.text.muted }}
            tickLine={false}
            axisLine={false}
            width={118}
          />
          <Tooltip
            cursor={{ fill: colors.surface.border, fillOpacity: 0.25 }}
            formatter={(v: number) => [`${v > 0 ? "+" : ""}${v.toFixed(2)}%`, "Projected change"]}
            contentStyle={{ fontSize: 12, borderRadius: 12, border: `1px solid ${colors.surface.border}` }}
          />
          <Bar dataKey="pct" radius={[0, 6, 6, 0]} barSize={20}>
            {rows.map((r) => (
              <Cell key={r.metric} fill={r.pct >= 0 ? colors.positive : colors.negative} />
            ))}
            <LabelList
              dataKey="pct"
              position="right"
              formatter={(v: number) => `${v > 0 ? "+" : ""}${v.toFixed(1)}%`}
              style={{ fontSize: 11, fontWeight: 700, fill: colors.text.primary }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
