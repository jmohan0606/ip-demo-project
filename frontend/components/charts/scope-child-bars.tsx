"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { colors } from "@/styles/tokens";
import type { ScopeChild } from "@/lib/api/scope";

const compactUsd = (v: number) =>
  `$${Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(v)}`;

/** LTM revenue by the scope's immediate children (divisions/regions/markets/
 * advisors). A comparison across peers -> vertical bars (dataviz rule). Each bar
 * is the child's summed real advisor revenue. Optional onSelect drills the shell
 * scope into the clicked child. */
export function ScopeChildBars({
  data,
  onSelect,
}: {
  data: ScopeChild[];
  onSelect?: (child: ScopeChild) => void;
}) {
  const rows = [...data].sort((a, b) => b.revenue_ltm - a.revenue_ltm);
  return (
    <div className="h-[240px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
          <CartesianGrid vertical={false} stroke={colors.surface.border} strokeOpacity={0.6} />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 10, fill: colors.text.muted }}
            tickLine={false}
            axisLine={{ stroke: colors.surface.border }}
            interval={0}
            angle={rows.length > 6 ? -20 : 0}
            textAnchor={rows.length > 6 ? "end" : "middle"}
            height={rows.length > 6 ? 48 : 24}
          />
          <YAxis
            tickFormatter={compactUsd}
            tick={{ fontSize: 10, fill: colors.text.muted }}
            tickLine={false}
            axisLine={false}
            width={48}
          />
          <Tooltip
            cursor={{ fill: colors.surface.border, fillOpacity: 0.25 }}
            contentStyle={{ borderRadius: 8, border: `1px solid ${colors.surface.border}`, fontSize: 12 }}
            formatter={(value: number) => [compactUsd(value), "Revenue (LTM)"]}
            labelFormatter={(label: string, payload) => {
              const c = payload?.[0]?.payload as ScopeChild | undefined;
              return c ? `${label} · ${c.advisor_count} advisors · goal ${c.avg_goal_attainment}%` : label;
            }}
          />
          <Bar
            isAnimationActive={false}
            dataKey="revenue_ltm"
            radius={[6, 6, 0, 0]}
            maxBarSize={64}
            cursor={onSelect ? "pointer" : undefined}
            onClick={(bar: unknown) => {
              const c = (bar as { payload?: ScopeChild }).payload;
              if (c && onSelect) onSelect(c);
            }}
          >
            {rows.map((r) => (
              <Cell key={r.scope_id} fill={colors.primary} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
