"use client";

import { useCallback, useEffect, useState } from "react";
import { ExternalLink, Users2 } from "lucide-react";

import { AccountMixDonut, type AccountMixSlice } from "@/components/charts/account-mix-donut";
import { AdvisorRevenueTrend, type AdvisorTrendPoint } from "@/components/charts/advisor-revenue-trend";
import { AiCoachingCard, type AiCoachingData } from "@/components/patterns/ai-coaching-card";
import { AiInsightSummary, type AiInsightData } from "@/components/patterns/ai-insight-summary";
import { useShellContext } from "@/components/layout/shell-context";
import { KpiStatCard } from "@/components/patterns/kpi-stat-card";
import { SeverityBadge } from "@/components/patterns/severity-badge";
import { apiClient } from "@/lib/api/client";
import { resolveScope } from "@/lib/api/hierarchy";
import { colors, type } from "@/styles/tokens";
import { formatCurrency } from "@/lib/utils";

interface Vertex { v_id: string; v_type: string; attributes: Record<string, unknown> }
interface CrmOpp {
  id: string; name?: string; stage?: string; status?: string; amount?: number;
  probability?: number; next_action?: string; expected_close_date?: string; days_to_close?: number | null;
}
interface SimilarBlock {
  source: { entity_id: string; name: string; [k: string]: unknown } | null;
  matches: Array<{ entity_id: string; name: string; similarity: number; [k: string]: unknown }>;
}
interface Advisor360Response {
  graph: Record<string, Vertex[]>;
  feature_snapshot: { snapshot_id: string; features: Record<string, number | string | null> } | null;
  agp_track: { enrolled: boolean; score?: number; band?: string; severity?: string; explanation?: string };
  crm_summary: { lead_summary: Record<string, number>; referral_summary: Record<string, number>; pipeline: Array<{ stage: string; opportunity_count: number; pipeline_amount: number }> };
  crm_opportunities: CrmOpp[];
  revenue_trend: AdvisorTrendPoint[];
  account_mix: AccountMixSlice[];
  segment_mix: Array<{ segment: string; count: number; aum: number }>;
  similar: { households: SimilarBlock | null; accounts: SimilarBlock | null };
}
interface AiResponse { insight: AiInsightData; coaching: AiCoachingData }
interface ChurnResponse {
  available: boolean; served?: boolean; quality_gate?: string; caveat?: string;
  households?: Array<{ household_id: string; propensity: number; band: string }>;
}

// Household churn band → color (Section 11.1 §3.5): elevated=red, watch=amber, stable=teal.
function churnTone(band: string): { fg: string; bg: string; border: string } {
  if (band === "elevated") return { fg: "#B91C1C", bg: "#FEF2F2", border: "#FECACA" };
  if (band === "watch") return { fg: "#B45309", bg: "#FFFBEB", border: "#FDE68A" };
  return { fg: "#0F766E", bg: "#F0FDFA", border: "#99F6E4" };
}

const money = (v: unknown) => (v === null || v === undefined ? "—" : formatCurrency(Number(v), { compact: true }));

// CRM outcome color-coding (CLAUDE.md 9.5): won=green, lost=red, negotiate/open=amber.
function outcomeTone(opp: CrmOpp): { label: string; fg: string; bg: string; border: string } {
  const s = (opp.status || "").toUpperCase();
  const stage = (opp.stage || "").toUpperCase();
  if (s === "WON") return { label: "Won", fg: "#0F766E", bg: "#F0FDFA", border: "#99F6E4" };
  if (s === "LOST") return { label: "Lost", fg: "#B91C1C", bg: "#FEF2F2", border: "#FECACA" };
  if (stage.includes("NEGOTIATE")) return { label: "Negotiate", fg: "#B45309", bg: "#FFFBEB", border: "#FDE68A" };
  return { label: stage ? stage.charAt(0) + stage.slice(1).toLowerCase() : "Open", fg: "#1D4ED8", bg: "#EFF6FF", border: "#BFDBFE" };
}

export function Advisor360Workspace() {
  const shell = useShellContext();
  const [advisors, setAdvisors] = useState<Array<{ advisor_id: string; advisor_name: string | null }>>([]);
  const [advisorId, setAdvisorId] = useState("A001");
  const [data, setData] = useState<Advisor360Response | null>(null);
  const [ai, setAi] = useState<AiResponse | null>(null);
  const [churn, setChurn] = useState<ChurnResponse | null>(null);
  const [referral, setReferral] = useState<{ available: boolean; tier?: string; percentile?: number; degree?: number; summary?: string } | null>(null);
  const [review, setReview] = useState<{ available: boolean; disclaimer?: string; false_positive_note?: string; flagged?: Array<{ household_id: string; review_reason: string; top_signals: Array<{ signal: string; value: number }> }> } | null>(null);
  const [busy, setBusy] = useState(false);
  const [bookTab, setBookTab] = useState<"households" | "accounts" | "activities">("households");

  useEffect(() => {
    apiClient
      .get<{ advisors: Array<{ advisor_id: string; advisor_name: string | null }> }>("/advisor/list")
      .then((response) => setAdvisors(response.advisors))
      .catch(() => setAdvisors([]));
  }, []);

  useEffect(() => {
    if (shell.scopeType === "Advisor") {
      setAdvisorId(shell.scopeId);
    } else {
      resolveScope(shell.scopeType, shell.scopeId)
        .then((r) => setAdvisorId(r.advisor_ids[0] ?? "A001"))
        .catch(() => undefined);
    }
  }, [shell.scopeType, shell.scopeId]);

  const load = useCallback(async () => {
    setBusy(true);
    setAi(null);
    setChurn(null);
    try {
      setData(await apiClient.get<Advisor360Response>(`/advisor/360/${advisorId}`));
      // AI card loads independently so the page paints without waiting on generation.
      apiClient.get<AiResponse>(`/advisor/360/${advisorId}/ai`).then(setAi).catch(() => setAi(null));
      // Household churn (Section 11.1) — real per-household model output when MODEL_CLIENT_MODE=real.
      apiClient.get<ChurnResponse>(`/predictions/household-churn/${advisorId}`).then(setChurn).catch(() => setChurn(null));
      // Referral Network Position (Section 11.1 §6 — PageRank over the real referral/book graph).
      apiClient.get<typeof referral>(`/graph-insights/referral/${advisorId}`).then(setReferral).catch(() => setReferral(null));
      // Activity Pattern Review (Section 11.1 §9 — Isolation Forest, care-framed).
      apiClient.get<typeof review>(`/predictions/activity-review/${advisorId}`).then(setReview).catch(() => setReview(null));
    } finally {
      setBusy(false);
    }
  }, [advisorId, shell.refreshNonce]);

  useEffect(() => { void load(); }, [load]);

  const advisor = data?.graph.advisor?.[0];
  const features = data?.feature_snapshot?.features ?? {};
  const churnByHousehold = new Map((churn?.households ?? []).map((h) => [h.household_id, h]));
  const counts = {
    households: data?.graph.households?.length ?? 0,
    accounts: data?.graph.accounts?.length ?? 0,
    activities: data?.graph.crm_activities?.length ?? 0,
  };
  const segTotal = (data?.segment_mix ?? []).reduce((s, x) => s + x.count, 0) || 1;

  return (
    <div className="space-y-4 p-6" style={{ backgroundColor: colors.surface.canvas, minHeight: "100vh" }}>
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className={type.pageTitle} style={{ color: colors.text.primary }}>
            Advisor 360 — {String(advisor?.attributes.advisor_name ?? advisorId)}
          </h1>
          <p className={type.body} style={{ color: colors.text.secondary }}>
            Book, CRM execution, AGP status and AI coaching assembled live from the graph (GQ-009). Scope-aware via the breadcrumb.
          </p>
        </div>
        <select
          value={advisorId}
          onChange={(event) => {
            const opt = advisors.find((a) => a.advisor_id === event.target.value);
            shell.setScope("Advisor", event.target.value, opt?.advisor_name ?? event.target.value);
          }}
          className="rounded-lg border px-2.5 py-1.5 text-[13px]"
          style={{ borderColor: colors.surface.border, color: colors.text.primary }}
        >
          {(advisors.length ? advisors : [{ advisor_id: "A001", advisor_name: null }]).map((option) => (
            <option key={option.advisor_id} value={option.advisor_id}>
              {option.advisor_id}{option.advisor_name ? ` — ${option.advisor_name}` : ""}
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <KpiStatCard label="Revenue LTM" value={money(features.revenue_ltm)} />
        <KpiStatCard label="AUM" value={money(features.aum_total)} />
        <KpiStatCard label="NNM 3M" value={money(features.nnm_3m)} />
        <KpiStatCard label="Households" value={String(counts.households)} />
      </div>

      {/* AI Insight Summary + AI Coaching Card (structured, per-advisor) */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {ai ? <AiInsightSummary data={ai.insight} /> : <div className="h-[320px] animate-pulse rounded-xl bg-slate-100" />}
        {ai ? <AiCoachingCard data={ai.coaching} /> : <div className="h-[320px] animate-pulse rounded-xl bg-slate-100" />}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="rounded-xl border bg-white p-4 shadow-sm lg:col-span-2" style={{ borderColor: colors.surface.border }}>
          <h2 className={type.cardTitle} style={{ color: colors.text.primary }}>Revenue Trend</h2>
          {data && data.revenue_trend?.length ? (
            <div className="mt-2"><AdvisorRevenueTrend data={data.revenue_trend} /></div>
          ) : (
            <div className="mt-2 h-[220px] animate-pulse rounded-lg bg-slate-100" />
          )}
        </div>
        <div className="rounded-xl border bg-white p-4 shadow-sm" style={{ borderColor: colors.surface.border }}>
          <h2 className={type.cardTitle} style={{ color: colors.text.primary }}>Book by Account Type</h2>
          {data && data.account_mix?.length ? (
            <div className="mt-3"><AccountMixDonut data={data.account_mix} /></div>
          ) : (
            <div className="mt-3 h-[180px] animate-pulse rounded-lg bg-slate-100" />
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* AGP status — only meaningful when enrolled (CLAUDE.md 9.5) */}
        <div className="rounded-xl border bg-white p-4 shadow-sm" style={{ borderColor: colors.surface.border }}>
          <div className="flex items-center justify-between">
            <h2 className={type.cardTitle} style={{ color: colors.text.primary }}>AGP Status</h2>
            {data?.agp_track.enrolled ? <SeverityBadge value={data.agp_track.severity ?? ""} /> : (
              <span className="rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.06em]" style={{ color: colors.text.muted, borderColor: colors.surface.border }}>Not Enrolled</span>
            )}
          </div>
          {data?.agp_track.enrolled ? (
            <div className="mt-2 space-y-1.5">
              <div className="flex items-baseline gap-2">
                <span className={type.kpiValue} style={{ color: colors.text.primary }}>{data.agp_track.score}</span>
                <span className={type.data} style={{ color: colors.text.muted }}>/100 risk · {data.agp_track.band}</span>
              </div>
              <p className={type.body} style={{ color: colors.text.secondary }}>{data.agp_track.explanation}</p>
            </div>
          ) : (
            <div className="mt-2 space-y-1">
              <p className={type.body} style={{ color: colors.text.secondary }}>
                This advisor is not enrolled in an AGP program, so no off-track risk is tracked. Book, CRM and AI coaching above apply to all advisors.
              </p>
            </div>
          )}
        </div>

        {/* Household segment breakdown (visual) */}
        <div className="rounded-xl border bg-white p-4 shadow-sm" style={{ borderColor: colors.surface.border }}>
          <h2 className={type.cardTitle} style={{ color: colors.text.primary }}>Households by Segment</h2>
          <div className="mt-3 space-y-2">
            {(data?.segment_mix ?? []).map((s) => (
              <div key={s.segment}>
                <div className="flex items-center justify-between">
                  <span className={type.data} style={{ color: colors.text.secondary }}>{s.segment}</span>
                  <span className={`font-mono ${type.data}`} style={{ color: colors.text.primary }}>{s.count} · {money(s.aum)}</span>
                </div>
                <div className="mt-1 h-2 w-full overflow-hidden rounded-full" style={{ backgroundColor: colors.surface.canvas }}>
                  <div className="h-full rounded-full" style={{ width: `${(s.count / segTotal) * 100}%`, backgroundColor: colors.primary }} />
                </div>
              </div>
            ))}
            {!data?.segment_mix?.length && <div className="h-[120px] animate-pulse rounded-lg bg-slate-100" />}
          </div>
        </div>

        {/* CRM pipeline summary */}
        <div className="rounded-xl border bg-white p-4 shadow-sm" style={{ borderColor: colors.surface.border }}>
          <h2 className={type.cardTitle} style={{ color: colors.text.primary }}>CRM Pipeline</h2>
          <div className="mt-2 grid grid-cols-2 gap-2">
            {[
              ["Leads Pending", data?.crm_summary.lead_summary?.pending],
              ["Leads Overdue", data?.crm_summary.lead_summary?.overdue],
              ["Referrals Pending", data?.crm_summary.referral_summary?.pending],
              ["Conversion %", data?.crm_summary.lead_summary?.conversion_rate_pct],
            ].map(([label, value]) => (
              <div key={String(label)} className="rounded-lg border px-2.5 py-2" style={{ borderColor: colors.surface.border }}>
                <div className={type.label} style={{ color: colors.text.muted }}>{label}</div>
                <div className="font-mono text-[16px] font-bold" style={{ color: colors.text.primary }}>{value ?? "—"}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* CRM execution — outcome-coded opportunity cards */}
      <div className="rounded-xl border bg-white p-4 shadow-sm" style={{ borderColor: colors.surface.border }}>
        <h2 className={type.cardTitle} style={{ color: colors.text.primary }}>CRM Execution · Opportunities</h2>
        <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-3">
          {(data?.crm_opportunities ?? []).map((opp) => {
            const tone = outcomeTone(opp);
            return (
              <div key={opp.id} className="rounded-lg border p-3" style={{ borderColor: tone.border, backgroundColor: tone.bg }}>
                <div className="flex items-start justify-between gap-2">
                  <span className={`${type.data} font-semibold`} style={{ color: colors.text.primary }}>{opp.name ?? opp.id}</span>
                  <span className="shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.05em]" style={{ color: tone.fg, backgroundColor: "#fff", border: `1px solid ${tone.border}` }}>{tone.label}</span>
                </div>
                <div className="mt-1.5 flex items-center justify-between">
                  <span className={`font-mono ${type.data}`} style={{ color: colors.text.primary }}>{money(opp.amount)}</span>
                  <span className={type.data} style={{ color: colors.text.muted }}>{opp.expected_close_date ?? ""}</span>
                </div>
                {opp.next_action && <p className={`mt-1 ${type.data}`} style={{ color: colors.text.secondary }}>Next: {opp.next_action}</p>}
              </div>
            );
          })}
          {!data?.crm_opportunities?.length && <p className={type.data} style={{ color: colors.text.muted }}>No CRM opportunities for this advisor.</p>}
        </div>
      </div>

      {/* Similar households / accounts — extends advisor similarity to other entity types */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {(["households", "accounts"] as const).map((kind) => {
          const block = data?.similar?.[kind] ?? null;
          return (
            <div key={kind} className="rounded-xl border bg-white p-4 shadow-sm" style={{ borderColor: colors.surface.border }}>
              <div className="flex items-center gap-2">
                <Users2 className="h-4 w-4" style={{ color: colors.aiAccent }} />
                <h2 className={type.cardTitle} style={{ color: colors.text.primary }}>Similar {kind === "households" ? "Households" : "Accounts"}</h2>
              </div>
              {block?.source ? (
                <>
                  <p className={`mt-1 ${type.data}`} style={{ color: colors.text.muted }}>
                    Nearest to <span className="font-semibold" style={{ color: colors.text.secondary }}>{block.source.name}</span> by embedding cosine similarity
                  </p>
                  <ul className="mt-2 space-y-1.5">
                    {block.matches.map((m) => (
                      <li key={m.entity_id} className="flex items-center gap-2">
                        <span className={`flex-1 ${type.data}`} style={{ color: colors.text.secondary }}>{m.name}</span>
                        <div className="h-1.5 w-20 overflow-hidden rounded-full" style={{ backgroundColor: colors.surface.canvas }}>
                          <div className="h-full rounded-full" style={{ width: `${Math.round(m.similarity * 100)}%`, backgroundColor: colors.aiAccent }} />
                        </div>
                        <span className={`w-10 text-right font-mono ${type.data}`} style={{ color: colors.text.primary }}>{Math.round(m.similarity * 100)}%</span>
                      </li>
                    ))}
                  </ul>
                </>
              ) : (
                <p className={`mt-2 ${type.data}`} style={{ color: colors.text.muted }}>No embedding available for this advisor&apos;s {kind}.</p>
              )}
            </div>
          );
        })}
      </div>

      {/* Activity Pattern Review (Section 11.1 §9 · Isolation Forest, care-framed) */}
      {review?.available && (review.flagged?.length ?? 0) > 0 ? (
        <div className="rounded-xl border px-4 py-3 shadow-sm" style={{ borderColor: "#FDE68A", background: "#FFFBEB" }}>
          <div className="flex items-center justify-between">
            <h2 className={type.cardTitle} style={{ color: "#92400E" }}>Activity Pattern Review</h2>
            <span className="rounded-full border px-2 py-0.5 text-[11px] font-semibold" style={{ color: "#92400E", background: "#FEF3C7", borderColor: "#FDE68A" }}>
              {review.flagged!.length} to review
            </span>
          </div>
          <p className="mt-1 text-[11px]" style={{ color: "#92400E" }}>{review.disclaimer}</p>
          <div className="mt-2 space-y-1.5">
            {review.flagged!.map((f) => (
              <div key={f.household_id} className="rounded-lg border bg-white px-3 py-1.5 text-[12px]" style={{ borderColor: "#FDE68A" }}>
                <div className="flex items-center justify-between">
                  <span className="font-semibold" style={{ color: colors.text.primary }}>{f.household_id} · {f.review_reason}</span>
                  <span className="text-[11px]" style={{ color: colors.text.muted }}>
                    {f.top_signals.map((s) => `${s.signal} ${s.value}`).join(" · ")}
                  </span>
                </div>
              </div>
            ))}
          </div>
          <p className="mt-2 text-[10px]" style={{ color: colors.text.muted }}>{review.false_positive_note}</p>
        </div>
      ) : null}

      {/* Referral Network Position (Section 11.1 §6 · PageRank) — with plain-language
          interpretation of what the score means and why it matters (12.4). */}
      {referral?.available ? (() => {
        const topPct = Math.round(100 - (referral.percentile ?? 0));
        const strong = topPct <= 15;
        const mid = topPct <= 40;
        const interp = strong
          ? `A top-${topPct}% referral connector — a strong mentor candidate. Highly central advisors move referrals across the firm's book, so they anchor AGP mentor/mentee pairing.`
          : mid
          ? `An above-average referral hub (top ${topPct}%). Well positioned to receive and pass referrals; a solid candidate for cross-market introductions.`
          : `Modest referral reach (top ${topPct}%). A growth opportunity — deepening ties with high-connector advisors would raise referral flow into this book.`;
        return (
          <div className="rounded-xl border bg-white px-4 py-3 shadow-sm" style={{ borderColor: colors.surface.border }}>
            <div className="flex items-center justify-between">
              <h2 className={type.cardTitle} style={{ color: colors.text.primary }}>Referral Network Position</h2>
              <span className="rounded-full border px-2 py-0.5 text-[11px] font-semibold"
                style={{ color: strong ? colors.positive : colors.aiAccent, background: strong ? "#F0FDFA" : "#EEF2FF", borderColor: strong ? "#CCFBF1" : "#C7D2FE" }}>
                PageRank · top {topPct}%
              </span>
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1">
              <div>
                <div className={type.label} style={{ color: colors.text.muted }}>Connections</div>
                <div className="text-[18px] font-bold" style={{ color: colors.text.primary }}>{referral.degree ?? "—"}</div>
              </div>
              <div>
                <div className={type.label} style={{ color: colors.text.muted }}>Firm Percentile</div>
                <div className="text-[18px] font-bold" style={{ color: colors.text.primary }}>{Math.round(referral.percentile ?? 0)}th</div>
              </div>
              <div className="min-w-[220px] flex-1">
                <p className={type.body} style={{ color: colors.text.secondary }}>{interp}</p>
              </div>
            </div>
            <p className="mt-2 text-[10px]" style={{ color: colors.text.muted }}>
              PageRank centrality over the real referral/book graph (advisor↔household↔referral edges). Higher = more central to how referrals flow.
            </p>
          </div>
        );
      })() : null}

      {/* Households table */}
      <div className="rounded-xl border bg-white shadow-sm" style={{ borderColor: colors.surface.border }}>
        <div className="flex items-center justify-between border-b px-4 py-2.5" style={{ borderColor: colors.surface.border }}>
          <div className="flex items-center gap-1">
            {([["households", `Households (${counts.households})`], ["accounts", `Accounts (${counts.accounts})`], ["activities", `Activities (${counts.activities})`]] as const).map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => setBookTab(key)}
                className="rounded-lg px-2.5 py-1 text-[12px] font-semibold transition"
                style={bookTab === key
                  ? { color: colors.primary, background: "#EFF6FF", border: `1px solid ${colors.primary}` }
                  : { color: colors.text.muted, border: "1px solid transparent" }}
              >
                {label}
              </button>
            ))}
          </div>
          <a href="/memory-explainability" className="inline-flex items-center gap-1 text-[11px] font-semibold" style={{ color: colors.primary }}>
            View AI lineage <ExternalLink className="h-3 w-3" />
          </a>
        </div>

        {/* Households tab */}
        {bookTab === "households" && (
          <>
            {churn?.available && churn.quality_gate !== "passed" ? (
              <p className="border-b px-4 py-1.5 text-[11px]" style={{ borderColor: colors.surface.border, color: colors.text.muted, background: "#FFFBEB" }}>
                Churn Risk column: {churn.caveat}
              </p>
            ) : null}
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b text-left" style={{ borderColor: colors.surface.border }}>
                    {["Household", "Name", "Segment", "AUM", "Status", "Churn Risk"].map((header) => (
                      <th key={header} className={`px-3 py-2 ${type.label}`} style={{ color: colors.text.muted }}>{header}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(data?.graph.households ?? []).slice(0, 12).map((household) => {
                    const c = churnByHousehold.get(household.v_id);
                    const tone = c ? churnTone(c.band) : null;
                    return (
                    <tr key={household.v_id} className="border-b last:border-0" style={{ borderColor: colors.surface.border }}>
                      <td className={`px-3 py-1.5 font-mono ${type.data}`} style={{ color: colors.text.primary }}>{household.v_id}</td>
                      <td className={`px-3 py-1.5 ${type.data}`} style={{ color: colors.text.secondary }}>{String(household.attributes.household_name ?? "—")}</td>
                      <td className={`px-3 py-1.5 ${type.data}`} style={{ color: colors.text.secondary }}>{String(household.attributes.segment ?? household.attributes.tier ?? "—")}</td>
                      <td className={`px-3 py-1.5 font-mono ${type.data}`} style={{ color: colors.text.secondary }}>{money(household.attributes.total_aum)}</td>
                      <td className={`px-3 py-1.5 ${type.data}`} style={{ color: colors.text.secondary }}>{String(household.attributes.status ?? "—")}</td>
                      <td className={`px-3 py-1.5 ${type.data}`}>
                        {c && tone ? (
                          <span className="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold"
                            style={{ color: tone.fg, background: tone.bg, borderColor: tone.border }}
                            title={`P(severe attrition)=${c.propensity}`}>
                            {c.band} · {(c.propensity * 100).toFixed(1)}%
                          </span>
                        ) : <span style={{ color: colors.text.muted }}>—</span>}
                      </td>
                    </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}

        {/* Accounts tab — the real per-account split (name, type, status, value) */}
        {bookTab === "accounts" && (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b text-left" style={{ borderColor: colors.surface.border }}>
                  {["Account", "Name", "Type", "Status", "Value"].map((header) => (
                    <th key={header} className={`px-3 py-2 ${type.label}`} style={{ color: colors.text.muted }}>{header}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(data?.graph.accounts ?? []).slice(0, 20).map((acct) => (
                  <tr key={acct.v_id} className="border-b last:border-0" style={{ borderColor: colors.surface.border }}>
                    <td className={`px-3 py-1.5 font-mono ${type.data}`} style={{ color: colors.text.primary }}>{acct.v_id}</td>
                    <td className={`px-3 py-1.5 ${type.data}`} style={{ color: colors.text.secondary }}>{String(acct.attributes.account_name ?? "—")}</td>
                    <td className={`px-3 py-1.5 ${type.data}`}>
                      <span className="rounded-full border px-2 py-0.5 text-[11px] font-semibold" style={{ color: colors.primary, background: "#EFF6FF", borderColor: "#BFDBFE" }}>
                        {String(acct.attributes.account_type ?? "—")}
                      </span>
                    </td>
                    <td className={`px-3 py-1.5 ${type.data}`} style={{ color: colors.text.secondary }}>{String(acct.attributes.status ?? "—")}</td>
                    <td className={`px-3 py-1.5 font-mono ${type.data}`} style={{ color: colors.text.secondary }}>{money(acct.attributes.current_value)}</td>
                  </tr>
                ))}
                {!(data?.graph.accounts ?? []).length && (
                  <tr><td colSpan={5} className={`px-3 py-4 text-center ${type.data}`} style={{ color: colors.text.muted }}>No accounts.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* Activities tab — real CRM activities (date, type, subject, status, next action) */}
        {bookTab === "activities" && (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b text-left" style={{ borderColor: colors.surface.border }}>
                  {["Date", "Type", "Subject", "Status", "Next Action", "Sentiment"].map((header) => (
                    <th key={header} className={`px-3 py-2 ${type.label}`} style={{ color: colors.text.muted }}>{header}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(data?.graph.crm_activities ?? []).slice(0, 20).map((act) => {
                  const s = String(act.attributes.sentiment ?? "");
                  const sTone = s === "POSITIVE" ? colors.positive : s === "NEGATIVE" ? colors.negative : colors.text.muted;
                  return (
                  <tr key={act.v_id} className="border-b last:border-0" style={{ borderColor: colors.surface.border }}>
                    <td className={`px-3 py-1.5 font-mono ${type.data}`} style={{ color: colors.text.secondary }}>{String(act.attributes.activity_date ?? "—")}</td>
                    <td className={`px-3 py-1.5 ${type.data}`}>
                      <span className="rounded-full border px-2 py-0.5 text-[11px] font-semibold" style={{ color: colors.text.secondary, background: colors.surface.canvas, borderColor: colors.surface.border }}>
                        {String(act.attributes.activity_type ?? "—")}
                      </span>
                    </td>
                    <td className={`px-3 py-1.5 ${type.data}`} style={{ color: colors.text.primary }}>{String(act.attributes.subject ?? "—")}</td>
                    <td className={`px-3 py-1.5 ${type.data}`} style={{ color: colors.text.secondary }}>{String(act.attributes.status ?? "—")}</td>
                    <td className={`px-3 py-1.5 ${type.data}`} style={{ color: colors.text.secondary }}>{String(act.attributes.next_action ?? "—")}</td>
                    <td className={`px-3 py-1.5 ${type.data} font-semibold`} style={{ color: sTone }}>{s || "—"}</td>
                  </tr>
                  );
                })}
                {!(data?.graph.crm_activities ?? []).length && (
                  <tr><td colSpan={6} className={`px-3 py-4 text-center ${type.data}`} style={{ color: colors.text.muted }}>No activities.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
        {busy ? <p className={`px-4 py-2 ${type.data}`} style={{ color: colors.text.muted }}>Loading…</p> : null}
      </div>
    </div>
  );
}
