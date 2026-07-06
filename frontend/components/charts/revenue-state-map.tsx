"use client";

import { useMemo, useState } from "react";
import { geoAlbersUsa, geoPath } from "d3-geo";
import { scaleLinear } from "d3-scale";
import { feature } from "topojson-client";
import type { Feature, Geometry } from "geojson";
import usAtlas from "us-atlas/states-10m.json";

import { colors, type } from "@/styles/tokens";
import { formatCurrency } from "@/lib/utils";

export interface StateRevenue {
  state: string;
  revenue: number;
  advisor_count: number;
}

// FIPS (us-atlas feature id) -> USPS 2-letter code, so we can join the topojson
// geometry to the by-branch-state revenue rows (which use 2-letter codes).
const FIPS_TO_USPS: Record<string, string> = {
  "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO", "09": "CT",
  "10": "DE", "11": "DC", "12": "FL", "13": "GA", "15": "HI", "16": "ID", "17": "IL",
  "18": "IN", "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME", "24": "MD",
  "25": "MA", "26": "MI", "27": "MN", "28": "MS", "29": "MO", "30": "MT", "31": "NE",
  "32": "NV", "33": "NH", "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
  "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD",
  "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA", "54": "WV",
  "55": "WI", "56": "WY",
};

const WIDTH = 975;
const HEIGHT = 610;

/**
 * Real US choropleth of revenue by branch state (advisor_in_branch -> branch.state).
 * Actual state geometry from the us-atlas TopoJSON projected with geoAlbersUsa —
 * NOT a tile grid of labelled boxes (CLAUDE.md 12.3, client-directed). Fill
 * intensity encodes revenue on a sequential blue scale; states with no revenue
 * render as faint context. Fully bundled/offline (no runtime map fetch). Hover a
 * state for its revenue + advisor count; a legend gradient carries the scale.
 */
export function RevenueStateMap({ data }: { data: StateRevenue[] }) {
  const [hover, setHover] = useState<{ code: string; name: string; x: number; y: number } | null>(null);

  const { paths, revByCode, maxRev } = useMemo(() => {
    const topo = usAtlas as unknown as { objects: { states: unknown } };
    const fc = feature(topo as never, topo.objects.states as never) as unknown as {
      features: Array<Feature<Geometry, { name: string }>>;
    };
    const projection = geoAlbersUsa().fitSize([WIDTH, HEIGHT], fc as never);
    const pathGen = geoPath(projection);
    const revMap: Record<string, StateRevenue> = {};
    for (const d of data) revMap[d.state.toUpperCase()] = d;
    const max = Math.max(1, ...data.map((d) => d.revenue));
    const built = fc.features.map((f) => {
      const fips = String(f.id).padStart(2, "0");
      const code = FIPS_TO_USPS[fips] ?? "";
      return { code, name: f.properties.name, d: pathGen(f) ?? "" };
    });
    return { paths: built, revByCode: revMap, maxRev: max };
  }, [data]);

  const fillScale = useMemo(
    () => scaleLinear<string>().domain([0, maxRev]).range(["#DBEAFE", colors.primary]).clamp(true),
    [maxRev],
  );

  const ranked = useMemo(() => [...data].sort((a, b) => b.revenue - a.revenue), [data]);
  const total = useMemo(() => data.reduce((s, d) => s + d.revenue, 0) || 1, [data]);

  return (
    <div className="flex flex-col gap-3 lg:flex-row">
      <div className="relative min-w-0 flex-1">
        <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="h-auto w-full" role="img" aria-label="US revenue choropleth">
          {paths.map((p) => {
            const rev = revByCode[p.code];
            return (
              <path
                key={p.name}
                d={p.d}
                fill={rev ? fillScale(rev.revenue) : "#F1F5F9"}
                stroke={colors.surface.card}
                strokeWidth={0.75}
                onMouseEnter={(e) => setHover({ code: p.code, name: p.name, x: e.nativeEvent.offsetX, y: e.nativeEvent.offsetY })}
                onMouseMove={(e) => setHover((h) => (h ? { ...h, x: e.nativeEvent.offsetX, y: e.nativeEvent.offsetY } : h))}
                onMouseLeave={() => setHover(null)}
                style={{ cursor: rev ? "pointer" : "default", transition: "fill 120ms" }}
              />
            );
          })}
        </svg>
        {hover && (
          <div
            className="pointer-events-none absolute z-10 rounded-lg border bg-white px-2.5 py-1.5 shadow-md"
            style={{ left: Math.min(hover.x + 10, WIDTH - 140), top: hover.y + 10, borderColor: colors.surface.border }}
          >
            <div className="text-[12px] font-semibold" style={{ color: colors.text.primary }}>{hover.name}</div>
            {revByCode[hover.code] ? (
              <div className={type.data} style={{ color: colors.text.secondary }}>
                {formatCurrency(revByCode[hover.code].revenue, { compact: true })} · {revByCode[hover.code].advisor_count} advisors
              </div>
            ) : (
              <div className={type.data} style={{ color: colors.text.muted }}>no revenue</div>
            )}
          </div>
        )}
        <div className="mt-1 flex items-center gap-2 px-1">
          <span className={type.label} style={{ color: colors.text.muted }}>Lower</span>
          <div className="h-2 flex-1 rounded-full" style={{ background: `linear-gradient(90deg, #DBEAFE, ${colors.primary})` }} />
          <span className={type.label} style={{ color: colors.text.muted }}>Higher</span>
          <span className={`ml-2 ${type.label}`} style={{ color: colors.text.muted }}>{data.length} states</span>
        </div>
      </div>

      <ul className="w-full shrink-0 space-y-1 lg:w-52">
        {ranked.slice(0, 8).map((d) => (
          <li key={d.state} className="flex items-center gap-2">
            <span className="inline-flex h-5 w-7 items-center justify-center rounded text-[10px] font-bold text-white" style={{ backgroundColor: fillScale(d.revenue) }}>{d.state}</span>
            <span className={`flex-1 font-mono ${type.data}`} style={{ color: colors.text.primary }}>{formatCurrency(d.revenue, { compact: true })}</span>
            <span className={`w-9 text-right font-mono ${type.data}`} style={{ color: colors.text.muted }}>{((d.revenue / total) * 100).toFixed(0)}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
