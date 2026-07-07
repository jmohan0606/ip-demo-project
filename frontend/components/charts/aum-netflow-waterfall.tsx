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

export interface NetFlowStep {
  label: string;
  kind: "base" | "increase" | "decrease" | "residual" | "total";
  value: number;
}

const compactUsd = (v: number) =>
  `${v < 0 ? "-" : ""}$${Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(Math.abs(v))}`;

// Kind → bar color (severity palette): base/total neutral, increase teal, decrease red,
// residual (market growth) primary blue.
const KIND_COLOR: Record<NetFlowStep["kind"], string> = {
  base: colors.text.muted,
  total: colors.text.primary,
  increase: colors.positive ?? "#14B8A6",
  decrease: colors.negative ?? "#DC2626",
  residual: colors.primary,
};

/**
 * AUM net-flows bridge/waterfall. Recharts has no native waterfall, so we use the
 * standard technique: a transparent "offset" bar lifts each floating step to its
 * running total, and a visible "delta" bar shows the signed change. Beginning/Ending
 * bars sit on the axis (offset 0). Every value is real from /scope/aum-net-flows.
 */
export function AumNetflowWaterfall({ steps }: { steps: NetFlowStep[] }) {
  let running = 0;
  const tops: number[] = [];
  const bottoms: number[] = [];
  const rows = steps.map((s) => {
    if (s.kind === "base" || s.kind === "total") {
      running = s.value;
      tops.push(s.value);
      bottoms.push(0);
      return { ...s, offset: 0, delta: s.value, top: s.value };
    }
    const start = running;
    const end = running + s.value;
    running = end;
    tops.push(Math.max(start, end));
    bottoms.push(Math.min(start, end));
    // offset = lower of start/end; delta = magnitude (bar floats between start and end)
    return { ...s, offset: Math.min(start, end), delta: Math.abs(s.value), top: end };
  });

  // AUM flows are ~1% of the base, so anchoring the axis at 0 makes the floating steps
  // invisible. Zoom the Y-axis to the band of change (running totals ± padding); the
  // Beginning/Ending pillars simply extend down off the truncated axis floor.
  const hi = Math.max(...tops);
  const lo = Math.min(...bottoms.filter((b) => b > 0), ...tops);
  const pad = Math.max((hi - lo) * 0.6, hi * 0.01);
  const floor = Math.max(0, lo - pad);
  const ceil = hi + pad * 0.4;

  return (
    <div className="h-[280px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 20, right: 12, bottom: 28, left: 8 }}>
          <CartesianGrid vertical={false} stroke={colors.surface.border} strokeOpacity={0.6} />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 10, fill: colors.text.muted }}
            tickLine={false}
            axisLine={{ stroke: colors.surface.border }}
            interval={0}
            angle={-18}
            textAnchor="end"
            height={54}
          />
          <YAxis
            tickFormatter={compactUsd}
            tick={{ fontSize: 10, fill: colors.text.muted }}
            tickLine={false}
            axisLine={false}
            width={52}
            domain={[floor, ceil]}
            allowDataOverflow
          />
          <Tooltip
            cursor={{ fill: colors.surface.border, fillOpacity: 0.25 }}
            contentStyle={{ borderRadius: 8, border: `1px solid ${colors.surface.border}`, fontSize: 12 }}
            formatter={(_v: number, _n: string, item: { payload?: NetFlowStep }) => {
              const p = item?.payload as NetFlowStep | undefined;
              return [compactUsd(p?.value ?? 0), p?.label ?? ""];
            }}
          />
          {/* Invisible spacer that lifts each floating bar to its running total. */}
          <Bar dataKey="offset" stackId="w" fill="transparent" isAnimationActive={false} />
          <Bar dataKey="delta" stackId="w" radius={[4, 4, 0, 0]} maxBarSize={56} isAnimationActive={false}>
            {rows.map((r, i) => (
              <Cell key={i} fill={KIND_COLOR[r.kind]} />
            ))}
            <LabelList
              dataKey="value"
              position="top"
              formatter={(v: number) => compactUsd(v)}
              style={{ fontSize: 9, fill: colors.text.secondary }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
