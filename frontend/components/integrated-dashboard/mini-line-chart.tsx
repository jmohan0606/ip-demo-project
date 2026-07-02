"use client";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid } from "recharts";
import { formatCurrency } from "@/lib/utils";
export function MiniLineChart({ data }: { data: any[] }) {
  return (
    <div className="h-[180px] w-full"><ResponsiveContainer width="100%" height="100%"><LineChart data={data} margin={{ top: 8, right: 10, left: 0, bottom: 0 }}>
      <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
      <XAxis dataKey="month" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
      <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => formatCurrency(Number(v))} width={58} tickLine={false} axisLine={false} />
      <Tooltip formatter={(v) => formatCurrency(Number(v))} />
      <Line type="monotone" dataKey="prior" stroke="#94a3b8" strokeWidth={2} dot={false} />
      <Line type="monotone" dataKey="revenue" stroke="#2563eb" strokeWidth={3} dot={{ r: 2 }} />
    </LineChart></ResponsiveContainer></div>
  );
}
