"use client";

import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";

import { colors, type } from "@/styles/tokens";

export interface ProjectionPoint {
  advisor_id: string;
  x: number;
  y: number;
  role: "target" | "similar" | "other";
  similarity: number | null;
}

// target vs similar are the CVD-safe salient pair (blue↔amber, validated);
// "other" is intentional neutral background (recedes, not a competing category).
const ROLE_STYLE = {
  other: { color: colors.text.muted, r: 4, label: "Other advisors" },
  similar: { color: colors.warning, r: 8, label: "Similar (top-k)" },
  target: { color: colors.primary, r: 11, label: "This advisor" },
} as const;

export function EmbeddingScatter({
  points,
  explainedVariance,
}: {
  points: ProjectionPoint[];
  explainedVariance: number[];
}) {
  const byRole = (role: ProjectionPoint["role"]) => points.filter((p) => p.role === role);
  // draw order: background first, target last (on top)
  const order: Array<ProjectionPoint["role"]> = ["other", "similar", "target"];

  return (
    <div>
      <div className="h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 8, right: 12, bottom: 8, left: 4 }}>
            <CartesianGrid stroke={colors.surface.border} strokeOpacity={0.5} />
            <XAxis
              type="number"
              dataKey="x"
              name="PC1"
              tick={{ fontSize: 10, fill: colors.text.muted }}
              tickLine={false}
              axisLine={{ stroke: colors.surface.border }}
              label={{ value: "PC1", position: "insideBottomRight", offset: -2, fontSize: 10, fill: colors.text.muted }}
            />
            <YAxis
              type="number"
              dataKey="y"
              name="PC2"
              tick={{ fontSize: 10, fill: colors.text.muted }}
              tickLine={false}
              axisLine={false}
              width={30}
              label={{ value: "PC2", position: "insideTopLeft", fontSize: 10, fill: colors.text.muted }}
            />
            <ZAxis type="number" range={[60, 60]} />
            {/* size is controlled per-role via the shape fn below, not ZAxis */}
            <Tooltip
              cursor={{ strokeDasharray: "3 3", stroke: colors.text.muted }}
              contentStyle={{ borderRadius: 8, border: `1px solid ${colors.surface.border}`, fontSize: 12 }}
              formatter={(value: number, name: string) => [value.toFixed(3), name]}
              labelFormatter={() => ""}
              content={({ payload }) => {
                const p = payload?.[0]?.payload as ProjectionPoint | undefined;
                if (!p) return null;
                return (
                  <div
                    className="rounded-lg border bg-white px-2 py-1 text-[11px] shadow-sm"
                    style={{ borderColor: colors.surface.border }}
                  >
                    <div style={{ color: colors.text.primary, fontWeight: 600 }}>{p.advisor_id}</div>
                    <div style={{ color: colors.text.muted }}>
                      {ROLE_STYLE[p.role].label}
                      {p.similarity != null ? ` · cos ${p.similarity.toFixed(3)}` : ""}
                    </div>
                  </div>
                );
              }}
            />
            {order.map((role) => {
              const style = ROLE_STYLE[role];
              return (
                <Scatter
                  key={role}
                  name={style.label}
                  data={byRole(role)}
                  fill={style.color}
                  isAnimationActive={false}
                  // radius per role = secondary encoding beyond hue (dataviz)
                  shape={(props: { cx?: number; cy?: number }) => (
                    <circle
                      cx={props.cx}
                      cy={props.cy}
                      r={style.r}
                      fill={style.color}
                      fillOpacity={role === "other" ? 0.5 : 0.95}
                      stroke={role === "other" ? "none" : colors.surface.card}
                      strokeWidth={role === "other" ? 0 : 1.5}
                    />
                  )}
                />
              );
            })}
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-1 flex flex-wrap items-center gap-3">
        {order
          .slice()
          .reverse()
          .map((role) => (
            <span key={role} className="flex items-center gap-1.5">
              <span
                className="rounded-full"
                style={{
                  backgroundColor: ROLE_STYLE[role].color,
                  width: role === "target" ? 11 : role === "similar" ? 8 : 6,
                  height: role === "target" ? 11 : role === "similar" ? 8 : 6,
                  opacity: role === "other" ? 0.5 : 1,
                }}
              />
              <span className={type.data} style={{ color: colors.text.secondary }}>{ROLE_STYLE[role].label}</span>
            </span>
          ))}
        <span className={`ml-auto ${type.data}`} style={{ color: colors.text.muted }}>
          PCA 8D→2D · PC1 {(explainedVariance[0] * 100).toFixed(0)}% · PC2 {(explainedVariance[1] * 100).toFixed(0)}% variance
        </span>
      </div>
    </div>
  );
}
