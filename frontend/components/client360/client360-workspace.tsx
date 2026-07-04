"use client";
import { useCallback, useEffect, useState } from "react";
import { Wallet, Landmark, Receipt, Sparkles, UserCircle } from "lucide-react";
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
            <CardHeader className="p-3">
              <CardTitle className="flex items-center gap-2 text-[13px]">
                <Sparkles className="h-4 w-4 text-primary" /> AI Recommendations
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 p-3 text-[12px]">
              {(profile?.recommendations ?? []).length === 0 && (
                <div className="p-3 text-center text-muted-foreground">None for this client.</div>
              )}
              {(profile?.recommendations ?? []).map((r) => (
                <div key={r.recommendation_id} className="rounded-xl border bg-ai-soft p-2">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">{r.title}</span>
                    <Badge variant={SEV_VARIANT[(r.severity ?? "").toUpperCase()] ?? "glass"}>{r.severity}</Badge>
                  </div>
                  <div className="mt-1 text-muted-foreground">
                    Impact {r.estimated_revenue_impact != null ? compactUsd(r.estimated_revenue_impact) : "—"} · conf{" "}
                    {r.confidence != null ? `${(r.confidence * 100).toFixed(0)}%` : "—"} · {r.status}
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
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
