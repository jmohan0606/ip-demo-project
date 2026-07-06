"use client";

import { useEffect, useState } from "react";
import { Area, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { apiClient } from "@/lib/api/client";
import { colors, type } from "@/styles/tokens";
import { formatCurrency } from "@/lib/utils";

interface ForecastResponse {
  history: Array<{ month: string; actual: number }>;
  forecast: Array<{ month: string; p50: number; p10: number; p90: number }>;
  model: { served_by: string; val_smape?: number; baseline_smape?: { seasonal_naive?: number; ma3?: number }; caveats?: string };
}

const axisMoney = (v: number) => formatCurrency(v, { compact: true });

export function RevenueForecastChart({ advisorId }: { advisorId: string }) {
  const [data, setData] = useState<ForecastResponse | null>(null);

  useEffect(() => {
    if (!advisorId) return;
    apiClient.get<ForecastResponse>(`/predictions/forecast/${advisorId}`).then(setData).catch(() => setData(null));
  }, [advisorId]);

  if (!data) return null;

  const last = data.history[data.history.length - 1];
  const rows = [
    ...data.history.map((h) => ({ month: h.month, actual: h.actual })),
    // bridge: start the forecast line + band at the last actual so they connect
    ...(last ? [{ month: last.month, p50: last.actual, lo: last.actual, span: 0 }] : []),
    ...data.forecast.map((f) => ({ month: f.month, p50: f.p50, lo: f.p10, span: f.p90 - f.p10 })),
  ];

  const m = data.model;
  const isGru = m.served_by?.includes("gru");

  return (
    <div className="rounded-xl border bg-white p-4 shadow-sm" style={{ borderColor: colors.surface.border }}>
      <div className="mb-2 flex items-center justify-between">
        <h2 className={type.cardTitle} style={{ color: colors.text.primary }}>Revenue Forecast · Next 6 Months</h2>
        <span className="rounded-full border px-2 py-0.5 text-[11px] font-semibold"
          style={{ color: colors.aiAccent, background: "#EEF2FF", borderColor: "#C7D2FE" }}>
          {isGru ? "✦ GRU forecast" : "seasonal-naive baseline"}
        </span>
      </div>
      <div style={{ width: "100%", height: 260 }}>
        <ResponsiveContainer>
          <ComposedChart data={rows} margin={{ top: 8, right: 12, left: 4, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={colors.surface.border} />
            <XAxis dataKey="month" tick={{ fontSize: 10, fill: colors.text.muted }} interval={5} />
            <YAxis tickFormatter={axisMoney} tick={{ fontSize: 10, fill: colors.text.muted }} width={54} />
            <Tooltip
              formatter={(v: number, name: string) => [formatCurrency(Number(v)), name]}
              contentStyle={{ fontSize: 11, borderRadius: 8, borderColor: colors.surface.border }}
            />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            {/* p10–p90 band via two stacked areas (base transparent, span translucent) */}
            <Area dataKey="lo" stackId="band" stroke="none" fill="transparent" legendType="none" name="p10" isAnimationActive={false} />
            <Area dataKey="span" stackId="band" stroke="none" fill={colors.aiAccent} fillOpacity={0.14}
              name="p10–p90 band" isAnimationActive={false} />
            <Line dataKey="actual" name="Actual" stroke={colors.primary} strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line dataKey="p50" name="Forecast (p50)" stroke={colors.aiAccent} strokeWidth={2}
              strokeDasharray="5 4" dot={false} isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <p className={`mt-2 ${type.data}`} style={{ color: colors.text.muted }}>
        Served by <b>{m.served_by}</b> · validation sMAPE {m.val_smape} vs seasonal-naive {m.baseline_smape?.seasonal_naive} /
        3-mo MA {m.baseline_smape?.ma3}. Band = empirical validation-residual p10–p90. {m.caveats}
      </p>
    </div>
  );
}
