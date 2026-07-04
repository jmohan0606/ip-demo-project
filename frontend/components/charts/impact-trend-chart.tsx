"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { colors, type } from "@/styles/tokens";

export interface ImpactPoint {
  round: number;
  accepted: number;
  implemented: number;
  rejected: number;
  cumulative_reward: number;
}

// three lines, so a legend is always present; semantic hues carry a label each.
const SERIES = [
  { key: "accepted", label: "Accepted", color: colors.positive },
  { key: "implemented", label: "Implemented", color: colors.primary },
  { key: "rejected", label: "Rejected", color: colors.negative },
] as const;

export function ImpactTrendChart({ data }: { data: ImpactPoint[] }) {
  return (
    <div>
      <div className="h-[240px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
            <CartesianGrid vertical={false} stroke={colors.surface.border} strokeOpacity={0.6} />
            <XAxis
              dataKey="round"
              tick={{ fontSize: 10, fill: colors.text.muted }}
              tickLine={false}
              axisLine={{ stroke: colors.surface.border }}
              label={{ value: "feedback round", position: "insideBottom", offset: -2, fontSize: 10, fill: colors.text.muted }}
            />
            <YAxis
              allowDecimals={false}
              tick={{ fontSize: 10, fill: colors.text.muted }}
              tickLine={false}
              axisLine={false}
              width={28}
            />
            <Tooltip
              cursor={{ stroke: colors.text.muted, strokeDasharray: "3 3" }}
              contentStyle={{ borderRadius: 8, border: `1px solid ${colors.surface.border}`, fontSize: 12 }}
              labelFormatter={(r) => `Round ${r}`}
            />
            <Legend
              verticalAlign="top"
              align="right"
              iconType="plainline"
              wrapperStyle={{ fontSize: 11, paddingBottom: 6 }}
            />
            {SERIES.map((s) => (
              <Line
                key={s.key}
                type="monotone"
                dataKey={s.key}
                name={s.label}
                stroke={s.color}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, strokeWidth: 0 }}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className={`mt-1 ${type.data}`} style={{ color: colors.text.muted }}>
        Cumulative feedback outcomes across the real recommendation set — x-axis is the feedback
        event sequence (the build has no calendar-time feedback history by design).
      </p>
    </div>
  );
}
