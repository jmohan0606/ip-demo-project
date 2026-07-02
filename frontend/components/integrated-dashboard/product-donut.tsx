"use client";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
const colors = ["#2563eb", "#06b6d4", "#8b5cf6", "#f97316", "#94a3b8"];
export function ProductDonut({ data }: { data: any[] }) {
  return (
    <div className="grid grid-cols-[150px_1fr] items-center gap-2">
      <div className="h-[150px]"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={data} dataKey="share" innerRadius={42} outerRadius={66} paddingAngle={2}>{data.map((_, i) => <Cell key={i} fill={colors[i % colors.length]} />)}</Pie><Tooltip formatter={(v) => `${v}%`} /></PieChart></ResponsiveContainer></div>
      <div className="space-y-2 text-[11px]">{data.map((item, i) => <div key={item.category} className="flex items-center justify-between gap-2"><span><span className="mr-1 inline-block h-2 w-2 rounded-full" style={{ background: colors[i % colors.length] }} />{item.category}</span><strong>{item.share}%</strong></div>)}</div>
    </div>
  );
}
