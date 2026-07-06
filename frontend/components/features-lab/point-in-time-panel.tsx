"use client";

import { useCallback, useEffect, useState } from "react";

import { apiClient } from "@/lib/api/client";
import { colors, type } from "@/styles/tokens";
import { formatCurrency } from "@/lib/utils";

interface SnapshotResp { snapshot_id: string; as_of?: string; features: Record<string, number | string | null> }

// Preset as-of dates across the modeled 36-month range (2023-08 … 2026-07).
const AS_OF_DATES = ["2024-07-31", "2025-01-31", "2025-07-31", "2026-01-31"];
const CURRENT = "2026-07-03";
// Features worth comparing over time (the ones that actually move with the time window).
const TRACKED: Array<[string, "currency" | "number" | "pct"]> = [
  ["revenue_ltm", "currency"], ["aum_total", "currency"], ["nnm_3m", "currency"],
  ["ncf_3m", "currency"], ["managed_revenue_ratio", "pct"], ["revenue_growth_3m_pct", "number"],
  ["household_count", "number"], ["peer_revenue_gap_pct", "number"],
];

function fmt(v: unknown, kind: string): string {
  if (v === null || v === undefined) return "—";
  const n = Number(v);
  if (kind === "currency") return formatCurrency(n, { compact: true });
  if (kind === "pct") return `${(n * 100).toFixed(1)}%`;
  return n.toLocaleString();
}

export function PointInTimePanel({ advisorId }: { advisorId: string }) {
  const [asOf, setAsOf] = useState(AS_OF_DATES[1]);
  const [past, setPast] = useState<SnapshotResp | null>(null);
  const [current, setCurrent] = useState<SnapshotResp | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!advisorId) return;
    setBusy(true);
    try {
      const [p, c] = await Promise.all([
        apiClient.get<SnapshotResp>(`/features/as-of/${advisorId}?as_of=${asOf}`),
        apiClient.get<SnapshotResp>(`/features/as-of/${advisorId}?as_of=${CURRENT}`),
      ]);
      setPast(p);
      setCurrent(c);
    } finally {
      setBusy(false);
    }
  }, [advisorId, asOf]);

  useEffect(() => { void load(); }, [load]);

  return (
    <div className="rounded-xl border bg-white p-4 shadow-sm" style={{ borderColor: colors.surface.border }}>
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className={type.cardTitle} style={{ color: colors.text.primary }}>Point-in-Time Feature Snapshot</h2>
          <p className={type.data} style={{ color: colors.text.muted }}>
            Temporal knowledge graph — the same features recomputed AS OF a past date from the real
            time-windowed graph facts, vs. today. Snapshots are versioned (FS_&lt;id&gt;_&lt;date&gt;).
          </p>
        </div>
        <div className="flex items-center gap-1">
          <span className={type.label} style={{ color: colors.text.muted }}>As of</span>
          <select value={asOf} onChange={(e) => setAsOf(e.target.value)}
            className="rounded-md border px-2 py-1 text-[12px]" style={{ borderColor: colors.surface.border }}>
            {AS_OF_DATES.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-[12px]">
          <thead>
            <tr className="border-b text-left text-[11px] uppercase" style={{ color: colors.text.muted }}>
              <th className="px-2 py-1.5">Feature</th>
              <th className="px-2 py-1.5 text-right">As of {asOf}</th>
              <th className="px-2 py-1.5 text-right">Today ({CURRENT})</th>
              <th className="px-2 py-1.5 text-right">Change</th>
            </tr>
          </thead>
          <tbody>
            {TRACKED.map(([name, kind]) => {
              const a = past?.features?.[name];
              const b = current?.features?.[name];
              const delta = a !== null && a !== undefined && b !== null && b !== undefined ? Number(b) - Number(a) : null;
              const up = delta !== null && delta > 0;
              const flat = delta === null || Math.abs(delta) < 1e-9;
              return (
                <tr key={name} className="border-b last:border-0" style={{ borderColor: colors.surface.border }}>
                  <td className="px-2 py-1.5 font-mono" style={{ color: colors.text.primary }}>{name}</td>
                  <td className="px-2 py-1.5 text-right font-mono" style={{ color: colors.text.secondary }}>{fmt(a, kind)}</td>
                  <td className="px-2 py-1.5 text-right font-mono" style={{ color: colors.text.secondary }}>{fmt(b, kind)}</td>
                  <td className="px-2 py-1.5 text-right font-mono font-semibold"
                    style={{ color: flat ? colors.text.muted : up ? colors.positive : colors.negative }}>
                    {flat ? "—" : `${up ? "▲" : "▼"} ${fmt(Math.abs(delta as number), kind)}`}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-[11px]" style={{ color: colors.text.muted }}>
        {busy ? "Computing…" : `Snapshots: ${past?.snapshot_id ?? "—"} vs ${current?.snapshot_id ?? "—"} · both computed live from time-windowed graph facts.`}
      </p>
    </div>
  );
}
