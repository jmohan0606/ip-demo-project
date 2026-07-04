"use client";

import { useCallback, useEffect, useState } from "react";

import { AccountMixDonut, type AccountMixSlice } from "@/components/charts/account-mix-donut";
import { AdvisorRevenueTrend, type AdvisorTrendPoint } from "@/components/charts/advisor-revenue-trend";
import { KpiStatCard } from "@/components/patterns/kpi-stat-card";
import { SeverityBadge } from "@/components/patterns/severity-badge";
import { apiClient } from "@/lib/api/client";
import { colors, type } from "@/styles/tokens";

interface Vertex {
  v_id: string;
  v_type: string;
  attributes: Record<string, unknown>;
}

interface Advisor360Response {
  graph: Record<string, Vertex[]>;
  feature_snapshot: { snapshot_id: string; features: Record<string, number | string | null> } | null;
  agp_track: {
    enrolled: boolean;
    score?: number;
    band?: string;
    severity?: string;
    explanation?: string;
  };
  crm_summary: {
    lead_summary: Record<string, number>;
    referral_summary: Record<string, number>;
    pipeline: Array<{ stage: string; opportunity_count: number; pipeline_amount: number }>;
  };
  revenue_trend: AdvisorTrendPoint[];
  account_mix: AccountMixSlice[];
}

const money = (value: unknown) =>
  value === null || value === undefined ? "—" : `$${Math.round(Number(value)).toLocaleString()}`;

export function Advisor360Workspace() {
  const [advisors, setAdvisors] = useState<Array<{ advisor_id: string; advisor_name: string | null }>>([]);
  const [advisorId, setAdvisorId] = useState("A001");
  const [data, setData] = useState<Advisor360Response | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    apiClient
      .get<{ advisors: Array<{ advisor_id: string; advisor_name: string | null }> }>("/advisor/list")
      .then((response) => setAdvisors(response.advisors))
      .catch(() => setAdvisors([]));
  }, []);

  const load = useCallback(async () => {
    setBusy(true);
    try {
      setData(await apiClient.get<Advisor360Response>(`/advisor/360/${advisorId}`));
    } finally {
      setBusy(false);
    }
  }, [advisorId]);

  useEffect(() => {
    void load();
  }, [load]);

  const advisor = data?.graph.advisor?.[0];
  const features = data?.feature_snapshot?.features ?? {};
  const counts = {
    households: data?.graph.households?.length ?? 0,
    accounts: data?.graph.accounts?.length ?? 0,
    activities: data?.graph.crm_activities?.length ?? 0,
    recommendations: data?.graph.recommendations?.length ?? 0,
  };

  return (
    <div className="space-y-4 p-6" style={{ backgroundColor: colors.surface.canvas, minHeight: "100vh" }}>
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className={type.pageTitle} style={{ color: colors.text.primary }}>
            Advisor 360 — {String(advisor?.attributes.advisor_name ?? advisorId)}
          </h1>
          <p className={type.body} style={{ color: colors.text.secondary }}>
            Book, CRM execution, AGP status and AI artifacts assembled live from the graph (GQ-009).
          </p>
        </div>
        <select
          value={advisorId}
          onChange={(event) => setAdvisorId(event.target.value)}
          className="rounded-lg border px-2.5 py-1.5 text-[13px]"
          style={{ borderColor: colors.surface.border, color: colors.text.primary }}
        >
          {(advisors.length ? advisors : [{ advisor_id: "A001", advisor_name: null }]).map((option) => (
            <option key={option.advisor_id} value={option.advisor_id}>
              {option.advisor_id}
              {option.advisor_name ? ` — ${option.advisor_name}` : ""}
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <KpiStatCard label="Revenue LTM" value={money(features.revenue_ltm)} />
        <KpiStatCard label="AUM" value={money(features.aum_total)} />
        <KpiStatCard label="NNM 3m" value={money(features.nnm_3m)} />
        <KpiStatCard label="Households" value={String(counts.households)} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="rounded-xl border bg-white p-4 shadow-sm lg:col-span-2" style={{ borderColor: colors.surface.border }}>
          <h2 className={type.cardTitle} style={{ color: colors.text.primary }}>Revenue trend</h2>
          {data && data.revenue_trend?.length ? (
            <div className="mt-2"><AdvisorRevenueTrend data={data.revenue_trend} /></div>
          ) : (
            <div className="mt-2 h-[220px] animate-pulse rounded-lg bg-slate-100" />
          )}
        </div>
        <div className="rounded-xl border bg-white p-4 shadow-sm" style={{ borderColor: colors.surface.border }}>
          <h2 className={type.cardTitle} style={{ color: colors.text.primary }}>Book by account type</h2>
          {data && data.account_mix?.length ? (
            <div className="mt-3"><AccountMixDonut data={data.account_mix} /></div>
          ) : (
            <div className="mt-3 h-[180px] animate-pulse rounded-lg bg-slate-100" />
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="rounded-xl border bg-white p-4 shadow-sm" style={{ borderColor: colors.surface.border }}>
          <div className="flex items-center justify-between">
            <h2 className={type.cardTitle} style={{ color: colors.text.primary }}>AGP status</h2>
            {data?.agp_track.enrolled ? <SeverityBadge value={data.agp_track.severity ?? ""} /> : null}
          </div>
          {data?.agp_track.enrolled ? (
            <div className="mt-2 space-y-1.5">
              <div className="flex items-baseline gap-2">
                <span className={type.kpiValue} style={{ color: colors.text.primary }}>
                  {data.agp_track.score}
                </span>
                <span className={type.data} style={{ color: colors.text.muted }}>
                  /100 risk · {data.agp_track.band}
                </span>
              </div>
              <p className={type.body} style={{ color: colors.text.secondary }}>{data.agp_track.explanation}</p>
            </div>
          ) : (
            <p className={`mt-2 ${type.data}`} style={{ color: colors.text.muted }}>Not enrolled in AGP.</p>
          )}
        </div>

        <div className="rounded-xl border bg-white p-4 shadow-sm" style={{ borderColor: colors.surface.border }}>
          <h2 className={type.cardTitle} style={{ color: colors.text.primary }}>CRM execution</h2>
          <div className="mt-2 grid grid-cols-2 gap-2">
            {[
              ["Leads pending", data?.crm_summary.lead_summary?.pending],
              ["Leads overdue", data?.crm_summary.lead_summary?.overdue],
              ["Referrals pending", data?.crm_summary.referral_summary?.pending],
              ["Conversion %", data?.crm_summary.lead_summary?.conversion_rate_pct],
            ].map(([label, value]) => (
              <div key={String(label)} className="rounded-lg border px-2.5 py-2" style={{ borderColor: colors.surface.border }}>
                <div className={type.label} style={{ color: colors.text.muted }}>{label}</div>
                <div className="font-mono text-[16px] font-bold" style={{ color: colors.text.primary }}>
                  {value ?? "—"}
                </div>
              </div>
            ))}
          </div>
          <div className="mt-2 space-y-1">
            {(data?.crm_summary.pipeline ?? []).map((stage) => (
              <div key={stage.stage} className="flex items-center justify-between">
                <span className={type.data} style={{ color: colors.text.secondary }}>{stage.stage}</span>
                <span className={`font-mono ${type.data}`} style={{ color: colors.text.primary }}>
                  {stage.opportunity_count} · {money(stage.pipeline_amount)}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-xl border bg-white p-4 shadow-sm" style={{ borderColor: colors.surface.border }}>
          <h2 className={type.cardTitle} style={{ color: colors.text.primary }}>AI artifacts</h2>
          <div className="mt-2 space-y-1.5">
            {[
              ["Predictions", data?.graph.predictions],
              ["AI opportunities", data?.graph.opportunities],
              ["Recommendations", data?.graph.recommendations],
              ["Feature snapshots", data?.graph.features],
              ["Memories", data?.graph.memories],
            ].map(([label, items]) => (
              <div key={String(label)} className="flex items-center justify-between">
                <span className={type.data} style={{ color: colors.text.secondary }}>{String(label)}</span>
                <span className={`font-mono ${type.data}`} style={{ color: colors.primary }}>
                  {(items as Vertex[] | undefined)?.length ?? 0}
                </span>
              </div>
            ))}
          </div>
          <p className={`mt-3 ${type.data}`} style={{ color: colors.text.muted }}>
            Drill into lineage on the Explainability page.
          </p>
        </div>
      </div>

      <div className="rounded-xl border bg-white shadow-sm" style={{ borderColor: colors.surface.border }}>
        <div className="border-b px-4 py-2.5" style={{ borderColor: colors.surface.border }}>
          <h2 className={type.cardTitle} style={{ color: colors.text.primary }}>
            Households ({counts.households}) · Accounts ({counts.accounts}) · Activities ({counts.activities})
          </h2>
        </div>
        <table className="w-full">
          <thead>
            <tr className="border-b text-left" style={{ borderColor: colors.surface.border }}>
              {["Household", "Name", "Segment", "Status"].map((header) => (
                <th key={header} className={`px-3 py-2 ${type.label}`} style={{ color: colors.text.muted }}>{header}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {(data?.graph.households ?? []).slice(0, 12).map((household) => (
              <tr key={household.v_id} className="border-b last:border-0" style={{ borderColor: colors.surface.border }}>
                <td className={`px-3 py-1.5 font-mono ${type.data}`} style={{ color: colors.text.primary }}>{household.v_id}</td>
                <td className={`px-3 py-1.5 ${type.data}`} style={{ color: colors.text.secondary }}>
                  {String(household.attributes.household_name ?? "—")}
                </td>
                <td className={`px-3 py-1.5 ${type.data}`} style={{ color: colors.text.secondary }}>
                  {String(household.attributes.segment ?? household.attributes.tier ?? "—")}
                </td>
                <td className={`px-3 py-1.5 ${type.data}`} style={{ color: colors.text.secondary }}>
                  {String(household.attributes.status ?? "—")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {busy ? (
          <p className={`px-4 py-2 ${type.data}`} style={{ color: colors.text.muted }}>Loading…</p>
        ) : null}
      </div>
    </div>
  );
}
