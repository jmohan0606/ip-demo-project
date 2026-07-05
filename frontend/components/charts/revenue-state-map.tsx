"use client";

import { useMemo, useState, type ReactElement } from "react";

import { colors, type } from "@/styles/tokens";
import { formatCurrency } from "@/lib/utils";

export interface StateRevenue {
  state: string;
  revenue: number;
  advisor_count: number;
}

/**
 * US state tile-grid cartogram (statebin) — a real geographic map of revenue by
 * branch state (advisor_in_branch -> branch.state). Each state sits in its
 * approximate US position; fill intensity encodes revenue on a sequential blue
 * scale. Zero-revenue states render as faint context tiles. No map library /
 * external asset needed — CSS-grid positioned, theme-safe, presentation quality.
 *
 * The tile layout is the widely-used 8-row x 12-col US grid.
 */
const GRID: Record<string, [number, number]> = {
  AK: [0, 0], ME: [0, 11],
  VT: [1, 10], NH: [1, 11],
  WA: [2, 1], ID: [2, 2], MT: [2, 3], ND: [2, 4], MN: [2, 5], IL: [2, 6], WI: [2, 7], MI: [2, 8], NY: [2, 9], RI: [2, 10], MA: [2, 11],
  OR: [3, 1], NV: [3, 2], WY: [3, 3], SD: [3, 4], IA: [3, 5], IN: [3, 6], OH: [3, 7], PA: [3, 8], NJ: [3, 9], CT: [3, 10],
  CA: [4, 1], UT: [4, 2], CO: [4, 3], NE: [4, 4], MO: [4, 5], KY: [4, 6], WV: [4, 7], VA: [4, 8], MD: [4, 9], DE: [4, 10],
  AZ: [5, 1], NM: [5, 2], KS: [5, 3], AR: [5, 4], TN: [5, 5], NC: [5, 6], SC: [5, 7], DC: [5, 8],
  OK: [6, 3], LA: [6, 4], MS: [6, 5], AL: [6, 6], GA: [6, 7],
  HI: [7, 0], TX: [7, 3], FL: [7, 8],
};

const ROWS = 8;
const COLS = 12;

// Sequential fill: light slate -> primary blue by revenue intensity (0..1).
function hexLerp(a: string, b: string, t: number): string {
  const pa = [1, 3, 5].map((i) => parseInt(a.slice(i, i + 2), 16));
  const pb = [1, 3, 5].map((i) => parseInt(b.slice(i, i + 2), 16));
  const mix = pa.map((v, i) => Math.round(v + (pb[i] - v) * t));
  return `#${mix.map((v) => v.toString(16).padStart(2, "0")).join("")}`;
}

export function RevenueStateMap({ data }: { data: StateRevenue[] }) {
  const [hover, setHover] = useState<string | null>(null);
  const byState = useMemo(() => Object.fromEntries(data.map((d) => [d.state, d])), [data]);
  const max = useMemo(() => Math.max(1, ...data.map((d) => d.revenue)), [data]);
  const total = useMemo(() => data.reduce((s, d) => s + d.revenue, 0) || 1, [data]);

  const cells: ReactElement[] = [];
  for (const [st, [r, c]] of Object.entries(GRID)) {
    const rec = byState[st];
    const t = rec ? 0.18 + 0.82 * (rec.revenue / max) : 0; // floor so smallest present state stays visible
    const fill = rec ? hexLerp("#DBEAFE", colors.primary, t) : "transparent";
    const active = rec != null;
    const isHover = hover === st;
    cells.push(
      <div
        key={st}
        style={{
          gridColumn: c + 1,
          gridRow: r + 1,
          backgroundColor: fill,
          borderColor: active ? (isHover ? colors.text.primary : "transparent") : colors.surface.border,
          color: active && t > 0.55 ? "#fff" : active ? colors.text.primary : colors.text.muted,
        }}
        className={`flex aspect-square items-center justify-center rounded-md border text-[10px] font-semibold transition-transform ${
          active ? "cursor-default" : "opacity-40"
        } ${isHover ? "scale-110 shadow-md" : ""}`}
        onMouseEnter={() => active && setHover(st)}
        onMouseLeave={() => setHover(null)}
        title={rec ? `${st} · ${formatCurrency(rec.revenue, { compact: true })} · ${rec.advisor_count} advisors` : st}
      >
        {st}
      </div>,
    );
  }

  const hoverRec = hover ? byState[hover] : null;
  const top = [...data].sort((a, b) => b.revenue - a.revenue).slice(0, 6);

  return (
    <div className="flex flex-col gap-4 lg:flex-row">
      <div className="min-w-0 flex-1">
        <div
          className="grid gap-1"
          style={{ gridTemplateColumns: `repeat(${COLS}, minmax(0, 1fr))`, gridTemplateRows: `repeat(${ROWS}, auto)` }}
        >
          {cells}
        </div>
        <div className="mt-3 flex items-center gap-2">
          <span className={type.label} style={{ color: colors.text.muted }}>Lower</span>
          <div
            className="h-2 flex-1 rounded-full"
            style={{ background: `linear-gradient(90deg, ${hexLerp("#DBEAFE", colors.primary, 0.18)}, ${colors.primary})` }}
          />
          <span className={type.label} style={{ color: colors.text.muted }}>Higher</span>
          <span className="ml-2 text-[11px] font-medium" style={{ color: colors.text.secondary }}>
            {hoverRec ? `${hoverRec.state}: ${formatCurrency(hoverRec.revenue, { compact: true })}` : `${data.length} states`}
          </span>
        </div>
      </div>
      <ul className="w-full shrink-0 space-y-1.5 lg:w-56">
        {top.map((d) => (
          <li key={d.state} className="flex items-center gap-2">
            <span
              className="flex h-5 w-6 shrink-0 items-center justify-center rounded text-[9px] font-bold text-white"
              style={{ backgroundColor: hexLerp("#DBEAFE", colors.primary, 0.18 + 0.82 * (d.revenue / max)) }}
            >
              {d.state}
            </span>
            <span className={`flex-1 font-mono ${type.data}`} style={{ color: colors.text.primary }}>
              {formatCurrency(d.revenue, { compact: true })}
            </span>
            <span className={`w-9 text-right font-mono ${type.data}`} style={{ color: colors.text.muted }}>
              {((d.revenue / total) * 100).toFixed(0)}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
