"use client";
import { type } from "@/styles/tokens";
import { useCallback, useEffect, useState } from "react";
import { Radar as RadarIcon, Users } from "lucide-react";
import { useShellContext } from "@/components/layout/shell-context";
import { apiClient } from "@/lib/api/client";
import { resolveScope } from "@/lib/api/hierarchy";
import { fetchPeerBenchmark, type PeerBenchmark } from "@/lib/api/peers";
import { PeerRadar } from "@/components/charts/peer-radar";
import { KpiStatCard } from "@/components/patterns/kpi-stat-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { ScopeType } from "@/lib/types/navigation";

const compactUsd = (v: number) =>
  `$${Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(v)}`;

export function PeerBenchmarkingWorkspace() {
  const shell = useShellContext();
  const [advisorId, setAdvisorId] = useState("A001");
  const [advisors, setAdvisors] = useState<Array<{ advisor_id: string; advisor_name: string | null }>>([]);
  const [data, setData] = useState<PeerBenchmark | null>(null);

  useEffect(() => {
    apiClient
      .get<{ advisors: Array<{ advisor_id: string; advisor_name: string | null }> }>("/advisor/list")
      .then((r) => setAdvisors(r.advisors))
      .catch(() => setAdvisors([]));
  }, []);

  useEffect(() => {
    if (shell.scopeType === "Advisor") setAdvisorId(shell.scopeId);
    else resolveScope(shell.scopeType, shell.scopeId).then((r) => setAdvisorId(r.advisor_ids[0] ?? "A001")).catch(() => undefined);
  }, [shell.scopeType, shell.scopeId]);

  const load = useCallback(async () => {
    // benchmark against the peer group defined by the current (rollup) scope
    const peerScope = shell.scopeType === "Advisor" ? "FIRM" : shell.scopeType.toUpperCase();
    const peerScopeId = shell.scopeType === "Advisor" ? "F001" : shell.scopeId;
    setData(await fetchPeerBenchmark(advisorId, peerScope, peerScopeId));
  }, [advisorId, shell.scopeType, shell.scopeId]);

  useEffect(() => {
    void load();
  }, [load]);

  const advisorName = data?.advisor_name ?? advisorId;
  const topStrength = data ? [...data.dimensions].sort((a, b) => b.advisor_percentile - a.advisor_percentile)[0] : null;
  const topGap = data ? [...data.dimensions].sort((a, b) => a.advisor_percentile - b.advisor_percentile)[0] : null;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <Badge variant="glass">Peer Benchmarking</Badge>
          <h2 className={`mt-2 ${type.pageTitle}`}>{advisorName} vs Peers</h2>
          <p className="text-[12px] text-muted-foreground">
            Percentile rank across {data?.dimensions.length ?? 0} metrics within a real peer group of{" "}
            {data?.peer_group_size ?? "—"} advisors, plus nearest peers from the similarity model.
          </p>
        </div>
        <select
          className="h-8 rounded-lg border border-border bg-background px-2 text-[12px]"
          value={advisorId}
          onChange={(e) => setAdvisorId(e.target.value)}
        >
          {advisors.length === 0 && <option value={advisorId}>{advisorId}</option>}
          {advisors.map((a) => (
            <option key={a.advisor_id} value={a.advisor_id}>{a.advisor_name ?? a.advisor_id}</option>
          ))}
        </select>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiStatCard label="Peer Group" value={String(data?.peer_group_size ?? "—")} />
        <KpiStatCard label="Metrics Compared" value={String(data?.dimensions.length ?? "—")} />
        <KpiStatCard
          label="Top Strength"
          value={topStrength ? `${topStrength.metric}` : "—"}
          delta={topStrength ? `${topStrength.advisor_percentile.toFixed(0)}th` : undefined}
          deltaPositive
        />
        <KpiStatCard
          label="Biggest Gap"
          value={topGap ? `${topGap.metric}` : "—"}
          delta={topGap ? `${topGap.advisor_percentile.toFixed(0)}th` : undefined}
          deltaPositive={false}
        />
      </div>

      <div className="grid gap-3 xl:grid-cols-[1fr_1fr]">
        <Card>
          <CardHeader className="p-3">
            <CardTitle className="flex items-center gap-2 text-[13px]">
              <RadarIcon className="h-4 w-4 text-primary" /> Percentile Radar
            </CardTitle>
          </CardHeader>
          <CardContent className="p-3">
            {data && <PeerRadar data={data.dimensions} advisorName={advisorName} />}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="p-3">
            <CardTitle className="text-[13px]">Metric Detail</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-[12px]">
                <thead>
                  <tr className="border-b text-left text-[10px] uppercase tracking-wide text-muted-foreground">
                    <th className="px-3 py-2">Metric</th>
                    <th className="px-3 py-2 text-right">Advisor</th>
                    <th className="px-3 py-2 text-right">Peer Median</th>
                    <th className="px-3 py-2 text-right">Percentile</th>
                  </tr>
                </thead>
                <tbody>
                  {(data?.dimensions ?? []).map((d) => (
                    <tr key={d.feature} className="border-b last:border-0">
                      <td className="px-3 py-2 font-medium">{d.metric}</td>
                      <td className="px-3 py-2 text-right font-mono">{d.advisor_value.toLocaleString()}</td>
                      <td className="px-3 py-2 text-right font-mono text-muted-foreground">{d.peer_median_value.toLocaleString()}</td>
                      <td className="px-3 py-2 text-right">
                        <Badge variant={d.advisor_percentile >= 50 ? "success" : "warning"}>
                          {d.advisor_percentile.toFixed(0)}th
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="p-3">
          <CardTitle className="flex items-center gap-2 text-[13px]">
            <Users className="h-4 w-4 text-primary" /> Nearest Peers (Similarity Model)
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-2 p-3 sm:grid-cols-2 xl:grid-cols-3">
          {(data?.nearest_peers ?? []).map((p) => (
            <button
              key={p.advisor_id}
              onClick={() => shell.setScope("Advisor" as ScopeType, p.advisor_id, p.advisor_name)}
              className="rounded-xl border bg-background/80 p-3 text-left text-[12px] hover:bg-muted/40"
            >
              <div className="flex items-center justify-between">
                <span className="font-bold">{p.advisor_name}</span>
                <Badge variant="glass">{p.similarity_score != null ? p.similarity_score.toFixed(2) : "—"}</Badge>
              </div>
              <div className="mt-1 text-muted-foreground">Revenue {compactUsd(p.revenue_ltm)}</div>
              <div className="mt-1 flex flex-wrap gap-1">
                {p.reasons.slice(0, 4).map((r) => (
                  <span key={r} className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">{r}</span>
                ))}
              </div>
            </button>
          ))}
        </CardContent>
      </Card>

      {data && (
        <div className="rounded-xl border bg-good-soft p-3 text-[11px] text-muted-foreground">
          <span className="font-semibold text-foreground">Evidence · </span>
          {data.evidence.source}. {data.evidence.peer_ids_resolved} peers resolved under {data.scope_type} {data.scope_id}.
        </div>
      )}
    </div>
  );
}
