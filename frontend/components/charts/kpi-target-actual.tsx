"use client";

import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { colors, type } from "@/styles/tokens";

export interface KpiHistoryPoint {
  label: string;
  target: number;
  actual: number;
}

/** Target-vs-Actual grouped bar chart over the milestone timeline for one KPI
 * (CLAUDE.md 9.12 drill-in). Includes a legend (9.5: "all charts get legends"). */
export function KpiTargetActual({ data, unit }: { data: KpiHistoryPoint[]; unit?: string | null }) {
  const fmt = (v: number) =>
    unit === "USD" ? `$${Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(v)}` : `${v}${unit === "PERCENT" ? "%" : ""}`;
  return (
    <div className="h-[220px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 4 }} barGap={2}>
          <CartesianGrid vertical={false} stroke={colors.surface.border} strokeOpacity={0.6} />
          <XAxis dataKey="label" tick={{ fontSize: 10, fill: colors.text.muted }} tickLine={false} axisLine={{ stroke: colors.surface.border }} />
          <YAxis tickFormatter={fmt} tick={{ fontSize: 10, fill: colors.text.muted }} tickLine={false} axisLine={false} width={44} />
          <Tooltip contentStyle={{ borderRadius: 8, border: `1px solid ${colors.surface.border}`, fontSize: 12 }} formatter={(v: number, n: string) => [fmt(v), n]} />
          <Legend wrapperStyle={{ fontSize: 11 }} iconType="circle" iconSize={8} />
          <Bar dataKey="target" name="Target" fill={colors.surface.border} radius={[4, 4, 0, 0]} maxBarSize={22} />
          <Bar dataKey="actual" name="Actual" fill={colors.primary} radius={[4, 4, 0, 0]} maxBarSize={22} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
