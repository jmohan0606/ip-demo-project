"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { colors, type } from "@/styles/tokens";

export interface AccountMixSlice {
  account_type: string;
  value: number;
  count: number;
}

// Categorical hues in FIXED order (dataviz non-negotiable) — validated set.
const SLICE_COLORS = [colors.primary, colors.positive, colors.aiAccent, colors.warning, "#0EA5E9"];

const usd = (v: number) => `$${Math.round(v).toLocaleString()}`;

/** Book composition by account type — a real categorical breakdown (household
 * segment is monoculture in the seed, so account type is the meaningful donut).
 * 2px surface gap between segments; legend + values give identity beyond color. */
export function AccountMixDonut({ data }: { data: AccountMixSlice[] }) {
  const total = data.reduce((sum, s) => sum + s.value, 0) || 1;
  return (
    <div className="flex items-center gap-3">
      <div className="h-[180px] w-[180px] shrink-0">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="account_type"
              innerRadius={52}
              outerRadius={82}
              paddingAngle={2}
              stroke={colors.surface.card}
              strokeWidth={2}
            >
              {data.map((slice, i) => (
                <Cell key={slice.account_type} fill={SLICE_COLORS[i % SLICE_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                borderRadius: 8,
                border: `1px solid ${colors.surface.border}`,
                fontSize: 12,
              }}
              formatter={(value: number, name: string) => [
                `${usd(value)} · ${((value / total) * 100).toFixed(0)}%`,
                name,
              ]}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className="min-w-0 flex-1 space-y-1.5">
        {data.map((slice, i) => (
          <li key={slice.account_type} className="flex items-center gap-2">
            <span
              className="h-2.5 w-2.5 shrink-0 rounded-sm"
              style={{ backgroundColor: SLICE_COLORS[i % SLICE_COLORS.length] }}
            />
            <span className={`flex-1 ${type.data}`} style={{ color: colors.text.secondary }}>
              {slice.account_type}
              <span style={{ color: colors.text.muted }}> · {slice.count} acct</span>
            </span>
            <span className={`font-mono ${type.data}`} style={{ color: colors.text.primary }}>
              {usd(slice.value)}
            </span>
            <span className={`w-9 text-right font-mono ${type.data}`} style={{ color: colors.text.muted }}>
              {((slice.value / total) * 100).toFixed(0)}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
