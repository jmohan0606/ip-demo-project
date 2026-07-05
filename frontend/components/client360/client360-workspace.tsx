"use client";
import { useCallback, useEffect, useState } from "react";
import { Wallet, Landmark, Receipt, Sparkles, UserCircle, Users2, GitBranch } from "lucide-react";
import { colors, type as typo } from "@/styles/tokens";
import { useShellContext } from "@/components/layout/shell-context";
import { resolveScope } from "@/lib/api/hierarchy";
import {
  fetchHouseholdsForAdvisor,
  fetchClientProfile,
  type ClientProfile,
  type HouseholdRef,
} from "@/lib/api/client360";
import { KpiStatCard } from "@/components/patterns/kpi-stat-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const compactUsd = (v: number) =>
  `$${Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(v)}`;

const SEV_VARIANT: Record<string, "success" | "warning" | "destructive" | "glass"> = {
  CRITICAL: "destructive", URGENT: "warning", ATTENTION: "warning", INFO: "glass",
};

export function Client360Workspace() {
  const shell = useShellContext();
  const [advisorId, setAdvisorId] = useState("A001");
  const [households, setHouseholds] = useState<HouseholdRef[]>([]);
  const [householdId, setHouseholdId] = useState<string | null>(null);
  const [profile, setProfile] = useState<ClientProfile | null>(null);

  useEffect(() => {
    if (shell.scopeType === "Advisor") setAdvisorId(shell.scopeId);
    else resolveScope(shell.scopeType, shell.scopeId).then((r) => setAdvisorId(r.advisor_ids[0] ?? "A001")).catch(() => undefined);
  }, [shell.scopeType, shell.scopeId]);

  useEffect(() => {
    fetchHouseholdsForAdvisor(advisorId)
      .then((h) => {
        setHouseholds(h);
        setHouseholdId(h[0]?.household_id ?? null);
      })
      .catch(() => setHouseholds([]));
  }, [advisorId]);

  const load = useCallback(async () => {
    if (!householdId) return;
    setProfile(await fetchClientProfile(householdId));
  }, [householdId]);

  useEffect(() => {
    void load();
  }, [load]);

  const s = profile?.summary;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <Badge variant="glass">Client Intelligence 360</Badge>
          <h2 className="mt-2 text-[22px] font-black">{profile?.household_name ?? "Client"} Profile</h2>
          <p className="text-[12px] text-muted-foreground">
            Real household profile — accounts, product holdings, transactions and AI
            recommendations, served by{" "}
            <strong>{profile?.serving_advisor.advisor_name ?? "—"}</strong>.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            className="h-8 rounded-lg border border-border bg-background px-2 text-[12px]"
            value={householdId ?? ""}
            onChange={(e) => setHouseholdId(e.target.value)}
          >
            {households.length === 0 && <option value="">No households</option>}
            {households.map((h) => (
              <option key={h.household_id} value={h.household_id}>
                {h.household_name} · {compactUsd(Number(h.total_aum ?? 0))}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiStatCard label="Total AUM" value={profile ? compactUsd(profile.total_aum) : "—"} />
        <KpiStatCard label="Accounts" value={String(s?.account_count ?? "—")} delta={s ? `${s.holding_count} holdings` : undefined} deltaPositive />
        <KpiStatCard label="Managed Ratio" value={s ? `${(s.managed_ratio * 100).toFixed(0)}%` : "—"} />
        <KpiStatCard label="Revenue (LTM)" value={s ? compactUsd(s.revenue_ltm) : "—"} />
      </div>

      <div className="grid gap-3 xl:grid-cols-[1fr_.9fr]">
        <Card>
          <CardHeader className="p-3">
            <CardTitle className="flex items-center gap-2 text-[13px]">
              <Wallet className="h-4 w-4 text-primary" /> Accounts &amp; Holdings
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 p-3">
            {(profile?.accounts ?? []).map((acc) => (
              <div key={acc.account_id} className="rounded-xl border bg-background/80 p-3 text-[12px]">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Landmark className="h-4 w-4 text-muted-foreground" />
                    <span className="font-bold">{acc.account_name}</span>
                    <Badge variant="glass" className="text-[10px]">{acc.account_type}</Badge>
                  </div>
                  <span className="font-mono font-semibold">{compactUsd(acc.current_value)}</span>
                </div>
                <div className="mt-2 flex flex-wrap gap-1">
                  {acc.holdings.map((h) => (
                    <span
                      key={h.product_id}
                      className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground"
                      title={`${h.risk_level ?? ""} risk${h.managed ? " · managed" : ""}`}
                    >
                      {h.product_name ?? h.product_id}
                      {h.managed && " ★"}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <div className="space-y-3">
          <Card>
            <CardHeader className="p-3">
              <CardTitle className="flex items-center gap-2 text-[13px]">
                <UserCircle className="h-4 w-4 text-primary" /> Client Overview
              </CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-2 p-3 text-[12px]">
              <Info label="Segment" value={profile?.segment ?? "—"} />
              <Info label="Risk Profile" value={profile?.risk_profile ?? "—"} />
              <Info label="Status" value={profile?.status ?? "—"} />
              <Info label="State" value={profile?.state ?? "—"} />
              <Info label="Advisor" value={profile?.serving_advisor.advisor_name ?? "—"} />
              <Info label="Transactions" value={String(s?.transaction_count ?? "—")} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between p-3">
              <CardTitle className="flex items-center gap-2 text-[13px]">
                <Sparkles className="h-4 w-4" style={{ color: colors.aiAccent }} /> AI Recommendations
              </CardTitle>
              <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em]" style={{ color: colors.aiAccent, backgroundColor: "#EEF2FF", border: "1px solid #C7D2FE" }}>✦ AI Generated</span>
            </CardHeader>
            <CardContent className="space-y-3 p-3 text-[12px]">
              {(profile?.recommendations ?? []).length === 0 && (
                <div className="p-3 text-center text-muted-foreground">None for this client.</div>
              )}
              {(profile?.recommendations ?? []).map((r) => (
                <div key={r.recommendation_id} className="rounded-xl border p-3" style={{ borderColor: colors.surface.border }}>
                  <div className="flex items-center justify-between">
                    <span className="font-semibold" style={{ color: colors.text.primary }}>{r.title}</span>
                    <Badge variant={SEV_VARIANT[(r.severity ?? "").toUpperCase()] ?? "glass"}>{r.severity}</Badge>
                  </div>
                  {r.action_text && <p className="mt-1" style={{ color: colors.text.secondary }}>{r.action_text}</p>}
                  <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-[11px]" style={{ color: colors.text.muted }}>
                    <span>Impact <span className="font-mono" style={{ color: colors.positive }}>{r.estimated_revenue_impact != null ? compactUsd(r.estimated_revenue_impact) : "—"}</span></span>
                    <span>Confidence <span className="font-mono">{r.confidence != null ? `${(r.confidence * 100).toFixed(0)}%` : "—"}</span></span>
                    <span>Priority <span className="font-mono">{r.priority_score ?? "—"}</span></span>
                    <span>Status <span className="font-semibold">{r.status}</span></span>
                  </div>

                  {/* HOW this was reached (CLAUDE.md 9.5) */}
                  {r.lineage && (r.lineage.reasoning_steps.length > 0 || r.lineage.sources.length > 0) && (
                    <div className="mt-2 rounded-lg border p-2" style={{ borderColor: colors.surface.border, backgroundColor: colors.surface.canvas }}>
                      <div className="flex items-center gap-1.5">
                        <GitBranch className="h-3 w-3" style={{ color: colors.aiAccent }} />
                        <span className={typo.label} style={{ color: colors.aiAccent }}>How this was reached</span>
                      </div>
                      {r.lineage.reasoning_steps.length > 0 && (
                        <ol className="mt-1.5 space-y-0.5">
                          {r.lineage.reasoning_steps.map((step, i) => (
                            <li key={i} className="flex gap-1.5">
                              <span className="font-mono text-[10px]" style={{ color: colors.text.muted }}>{i + 1}.</span>
                              <span style={{ color: colors.text.secondary }}>{step}</span>
                            </li>
                          ))}
                        </ol>
                      )}
                      {r.lineage.evidence.length > 0 && (
                        <div className="mt-1.5 flex flex-wrap gap-1">
                          {r.lineage.evidence.map((e) => (
                            <span key={e.label} className="rounded border px-1.5 py-0.5 text-[10px]" style={{ borderColor: colors.surface.border, color: colors.text.secondary }}>
                              {e.label}: <span className="font-mono" style={{ color: colors.text.primary }}>{String(e.value)}</span>
                            </span>
                          ))}
                        </div>
                      )}
                      {r.lineage.sources.length > 0 && (
                        <div className="mt-1.5 flex flex-wrap gap-1">
                          {r.lineage.sources.map((sc) => (
                            <span key={sc.ref} className="rounded-full px-2 py-0.5 text-[10px] font-medium" style={{ backgroundColor: "#EEF2FF", color: colors.aiAccent }} title={sc.detail}>
                              {sc.type} · {sc.ref}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Similar households / accounts / portfolios (CLAUDE.md 9.5) */}
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        {(["households", "accounts"] as const).map((kind) => {
          const block = profile?.similar?.[kind] ?? null;
          return (
            <Card key={kind}>
              <CardHeader className="p-3">
                <CardTitle className="flex items-center gap-2 text-[13px]">
                  <Users2 className="h-4 w-4" style={{ color: colors.aiAccent }} /> Similar {kind === "households" ? "Households" : "Accounts / Portfolios"}
                </CardTitle>
              </CardHeader>
              <CardContent className="p-3 text-[12px]">
                {block?.source ? (
                  <>
                    <p className="mb-2" style={{ color: colors.text.muted }}>
                      Nearest to <span className="font-semibold" style={{ color: colors.text.secondary }}>{block.source.name}</span> by embedding cosine similarity
                    </p>
                    <ul className="space-y-1.5">
                      {block.matches.map((m) => (
                        <li key={m.entity_id} className="flex items-center gap-2">
                          <span className="flex-1" style={{ color: colors.text.secondary }}>{m.name}</span>
                          <div className="h-1.5 w-24 overflow-hidden rounded-full" style={{ backgroundColor: colors.surface.canvas }}>
                            <div className="h-full rounded-full" style={{ width: `${Math.round(m.similarity * 100)}%`, backgroundColor: colors.aiAccent }} />
                          </div>
                          <span className="w-10 text-right font-mono" style={{ color: colors.text.primary }}>{Math.round(m.similarity * 100)}%</span>
                        </li>
                      ))}
                    </ul>
                  </>
                ) : (
                  <p style={{ color: colors.text.muted }}>No embedding available for this {kind === "households" ? "household" : "account"}.</p>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      <Card>
        <CardHeader className="p-3">
          <CardTitle className="flex items-center gap-2 text-[13px]">
            <Receipt className="h-4 w-4 text-primary" /> Recent Transactions
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-[12px]">
              <thead>
                <tr className="border-b text-left text-[10px] uppercase tracking-wide text-muted-foreground">
                  <th className="px-3 py-2">Date</th>
                  <th className="px-3 py-2">Type</th>
                  <th className="px-3 py-2 text-right">Revenue</th>
                  <th className="px-3 py-2 text-right">Gross</th>
                </tr>
              </thead>
              <tbody>
                {(profile?.transactions ?? []).map((t) => (
                  <tr key={t.transaction_id} className="border-b last:border-0">
                    <td className="px-3 py-2 font-mono text-[11px]">{t.transaction_date}</td>
                    <td className="px-3 py-2">{t.transaction_type}</td>
                    <td className="px-3 py-2 text-right font-mono">{compactUsd(t.revenue_amount)}</td>
                    <td className="px-3 py-2 text-right font-mono text-muted-foreground">{compactUsd(t.gross_amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {profile && (
        <div className="rounded-xl border bg-good-soft p-3 text-[11px] text-muted-foreground">
          <span className="font-semibold text-foreground">Evidence · </span>{profile.evidence.source}
        </div>
      )}
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-background/70 px-3 py-2">
      <div className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="font-semibold">{value}</div>
    </div>
  );
}
