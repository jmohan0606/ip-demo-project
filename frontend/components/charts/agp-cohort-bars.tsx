"use client";

import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { colors, severity } from "@/styles/tokens";
import type { AgpCohortSummary } from "@/lib/api/agp";

const STATUS_COLOR: Record<string, string> = {
  COMPLETED: colors.positive,
  ON_TRACK: colors.primary,
  UPCOMING: colors.text.muted,
  AT_RISK: severity.urgent.fg,
};

/** Milestone progress records by status across the scope's AGP cohort — a
 * comparison across categories -> bars (dataviz rule). Real counts from the
 * cohort-summary aggregation. */
export function AgpCohortBars({ data }: { data: AgpCohortSummary["milestone_summary"] }) {
  const rows = [...data].sort((a, b) => b.progress_count - a.progress_count);
  return (
    <div className="h-[220px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
          <CartesianGrid vertical={false} stroke={colors.surface.border} strokeOpacity={0.6} />
          <XAxis
            dataKey="milestone_status"
            tick={{ fontSize: 10, fill: colors.text.muted }}
            tickLine={false}
            axisLine={{ stroke: colors.surface.border }}
            tickFormatter={(s: string) => s.replace("_", " ")}
          />
          <YAxis tick={{ fontSize: 10, fill: colors.text.muted }} tickLine={false} axisLine={false} width={32} />
          <Tooltip
            cursor={{ fill: colors.surface.border, fillOpacity: 0.25 }}
            contentStyle={{ borderRadius: 8, border: `1px solid ${colors.surface.border}`, fontSize: 12 }}
            formatter={(v: number, _n, p) => [
              `${v} records · ${(p.payload as { avg_attainment_pct: number }).avg_attainment_pct}% avg attainment`,
              "Milestones",
            ]}
          />
          <Bar dataKey="progress_count" radius={[6, 6, 0, 0]} maxBarSize={72}>
            {rows.map((r) => (
              <Cell key={r.milestone_status} fill={STATUS_COLOR[r.milestone_status] ?? colors.primary} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
