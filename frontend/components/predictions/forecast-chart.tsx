"use client";

import { Area, AreaChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ForecastPoint } from "@/lib/types/predictions_workspace";
import { formatCurrency } from "@/lib/utils";

export function ForecastChart({ data }: { data: ForecastPoint[] }) {
  return (
    <div className="h-[340px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 12, right: 20, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.18} />
          <XAxis dataKey="period" tickLine={false} axisLine={false} />
          <YAxis tickFormatter={(value) => formatCurrency(Number(value))} tickLine={false} axisLine={false} width={80} />
          <Tooltip formatter={(value) => formatCurrency(Number(value))} />
          <Legend />
          <Area type="monotone" dataKey="upperBound" name="Upper bound" stroke="#94A3B8" fill="#94A3B8" fillOpacity={0.08} />
          <Area type="monotone" dataKey="forecast" name="Forecast" stroke="#2563EB" strokeWidth={3} fill="#2563EB" fillOpacity={0.18} />
          <Area type="monotone" dataKey="baseline" name="Baseline" stroke="#7C3AED" strokeWidth={2} fill="#7C3AED" fillOpacity={0.08} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
