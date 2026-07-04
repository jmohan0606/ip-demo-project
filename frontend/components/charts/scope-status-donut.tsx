"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { colors, severity, type } from "@/styles/tokens";
import type { ScopeStatusDistribution } from "@/lib/api/scope";

// AGP-004 track bands -> severity palette (on_track is a good state -> teal).
const BANDS: Array<{ key: keyof ScopeStatusDistribution; label: string; color: string }> = [
  { key: "on_track", label: "On Track", color: colors.positive },
  { key: "attention", label: "Attention", color: severity.attention.fg },
  { key: "urgent", label: "Urgent", color: severity.urgent.fg },
  { key: "critical", label: "Critical", color: severity.critical.fg },
];

/** Advisor count by AGP status band under the current scope — categorical
 * breakdown, so a donut (dataviz rule). Counts are real per-advisor
 * agp_risk_score classifications, not invented proportions. */
export function ScopeStatusDonut({ data }: { data: ScopeStatusDistribution }) {
  const slices = BANDS.map((b) => ({ ...b, value: data[b.key] })).filter((s) => s.value > 0);
  const total = slices.reduce((sum, s) => sum + s.value, 0) || 1;
  return (
    <div className="flex items-center gap-3">
      <div className="h-[164px] w-[164px] shrink-0">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={slices}
              dataKey="value"
              nameKey="label"
              innerRadius={46}
              outerRadius={74}
              paddingAngle={2}
              stroke={colors.surface.card}
              strokeWidth={2}
            >
              {slices.map((s) => (
                <Cell key={s.key} fill={s.color} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{ borderRadius: 8, border: `1px solid ${colors.surface.border}`, fontSize: 12 }}
              formatter={(value: number, name: string) => [
                `${value} advisor${value === 1 ? "" : "s"} · ${((value / total) * 100).toFixed(0)}%`,
                name,
              ]}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className="min-w-0 flex-1 space-y-1.5">
        {BANDS.map((b) => (
          <li key={b.key} className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 shrink-0 rounded-sm" style={{ backgroundColor: b.color }} />
            <span className={`flex-1 ${type.data}`} style={{ color: colors.text.secondary }}>
              {b.label}
            </span>
            <span className={`font-mono ${type.data}`} style={{ color: colors.text.primary }}>
              {data[b.key]}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
