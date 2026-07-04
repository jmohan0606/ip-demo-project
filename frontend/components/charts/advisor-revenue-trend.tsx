"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { colors, type } from "@/styles/tokens";

export interface AdvisorTrendPoint {
  label: string;
  revenue: number;
  transaction_count?: number;
}

const compactUsd = (v: number) =>
  `$${Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(v)}`;

/** Monthly revenue trend — single series, so the chart title names it and no
 * legend box is needed (dataviz rule). Thin 2px line, recessive grid, hover
 * tooltip. Reads GQ-005 monthly data — no invented points. */
export function AdvisorRevenueTrend({ data }: { data: AdvisorTrendPoint[] }) {
  return (
    <div>
      <div className="h-[220px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
            <CartesianGrid vertical={false} stroke={colors.surface.border} strokeOpacity={0.6} />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 10, fill: colors.text.muted }}
              tickLine={false}
              axisLine={{ stroke: colors.surface.border }}
              interval="preserveStartEnd"
              minTickGap={26}
            />
            <YAxis
              tickFormatter={compactUsd}
              tick={{ fontSize: 10, fill: colors.text.muted }}
              tickLine={false}
              axisLine={false}
              width={44}
              // trend line: non-zero baseline fitted to the data range so the
              // month-to-month movement is visible (tooltip carries absolutes).
              domain={[
                (min: number) => Math.floor((min - 2000) / 1000) * 1000,
                (max: number) => Math.ceil((max + 2000) / 1000) * 1000,
              ]}
            />
            <Tooltip
              cursor={{ stroke: colors.text.muted, strokeDasharray: "3 3" }}
              contentStyle={{
                borderRadius: 8,
                border: `1px solid ${colors.surface.border}`,
                fontSize: 12,
                boxShadow: "0 4px 18px rgba(15,23,42,.10)",
              }}
              formatter={(value: number, _n, item) => [
                `${compactUsd(value)} · ${(item?.payload as AdvisorTrendPoint)?.transaction_count ?? 0} txns`,
                "Revenue",
              ]}
            />
            <Line
              type="monotone"
              dataKey="revenue"
              stroke={colors.primary}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, strokeWidth: 0 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className={`mt-1 ${type.data}`} style={{ color: colors.text.muted }}>
        Monthly revenue · {data.length} months (GQ-005, transactions aggregated per period).
      </p>
    </div>
  );
}
