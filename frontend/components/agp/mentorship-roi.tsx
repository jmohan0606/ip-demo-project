"use client";
import { useEffect, useState } from "react";
import { Users2, TrendingUp } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { WhyTrace } from "@/components/patterns/why-trace";
import { apiClient } from "@/lib/api/client";
import { formatEntity } from "@/lib/utils";

interface MentorPair {
  mentee_id: string; mentee_name: string; mentee_risk: number; mentee_revenue_ltm: number;
  mentor_id: string; mentor_name: string; mentor_revenue_ltm: number;
  mentor_referral_percentile: number | null; similarity: number; rationale: string;
}
interface PairingPayload {
  model: string; pairs: MentorPair[];
  unmatched: Array<{ mentee_id: string; mentee_name: string; mentee_risk: number; reason: string }>;
  methodology: string;
  evidence: { mentee_count: number; mentor_pool: number; candidate_edges: number; source: string };
}
interface RoiRow {
  advisor_id: string; advisor_name: string; cohort: string | null; enrolled_since: string | null;
  program_month: number | null; growth_pct: number; peer_baseline_pct: number | null; uplift_pp: number | null;
  peer_group: Array<{ advisor_id: string; advisor_name: string; similarity: number }>;
}
interface RoiPayload {
  available: boolean; model: string; window_months: number; latest_data_month: string;
  rows: RoiRow[];
  summary: { enrolled_measured: number; avg_uplift_pp: number | null; outperforming_baseline: number; share_outperforming_pct: number | null };
  methodology: string; caveats: string;
}

const usd = (v: number) => `$${Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(v)}`;

/** Section 10 — GNN mentor/mentee pairing + AGP program ROI (fair peer baseline). */
export function MentorshipRoi() {
  const [pairing, setPairing] = useState<PairingPayload | null>(null);
  const [roi, setRoi] = useState<RoiPayload | null>(null);

  useEffect(() => {
    apiClient.get<PairingPayload>("/agp/mentor-pairing").then(setPairing).catch(() => setPairing(null));
    apiClient.get<RoiPayload>("/agp/program-roi").then(setRoi).catch(() => setRoi(null));
  }, []);

  return (
    <div className="grid gap-3 xl:grid-cols-2">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between p-3">
          <CardTitle className="flex items-center gap-2 text-[13px]">
            <Users2 className="h-4 w-4 text-primary" /> Mentor / Mentee Pairing (GNN)
            {pairing && (
              <WhyTrace trace={{
                source: pairing.evidence.source,
                computation: pairing.methodology,
                link: "/feature-store",
                linkLabel: "Open Embeddings & Similarity",
              }} />
            )}
          </CardTitle>
          {pairing && <Badge variant="glass">{pairing.model}</Badge>}
        </CardHeader>
        <CardContent className="p-0">
          {!pairing ? (
            <div className="p-6 text-center text-[12px] text-muted-foreground">Computing pairings…</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-[12px]">
                <thead>
                  <tr className="border-b text-left text-[10px] uppercase tracking-wide text-muted-foreground">
                    <th className="px-3 py-2">Mentee (risk)</th>
                    <th className="px-3 py-2">Mentor</th>
                    <th className="px-3 py-2 text-right">Similarity</th>
                    <th className="px-3 py-2">Why this pairing</th>
                  </tr>
                </thead>
                <tbody>
                  {pairing.pairs.map((p) => (
                    <tr key={p.mentee_id} className="border-b align-top last:border-0">
                      <td className="px-3 py-2 font-medium">
                        {formatEntity(p.mentee_id, p.mentee_name)}
                        <Badge variant={p.mentee_risk >= 85 ? "destructive" : "warning"} className="ml-1.5">{p.mentee_risk}</Badge>
                      </td>
                      <td className="px-3 py-2">{formatEntity(p.mentor_id, p.mentor_name)}</td>
                      <td className="px-3 py-2 text-right font-mono text-teal-700">{p.similarity.toFixed(2)}</td>
                      <td className="px-3 py-2 text-[11px] text-muted-foreground">{p.rationale}</td>
                    </tr>
                  ))}
                  {pairing.unmatched.map((u) => (
                    <tr key={u.mentee_id} className="border-b bg-amber-50/40 last:border-0">
                      <td className="px-3 py-2 font-medium">{formatEntity(u.mentee_id, u.mentee_name)}</td>
                      <td className="px-3 py-2 text-muted-foreground" colSpan={3}>Unmatched — {u.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between p-3">
          <CardTitle className="flex items-center gap-2 text-[13px]">
            <TrendingUp className="h-4 w-4 text-primary" /> AGP Program ROI (vs Fair Peer Baseline)
            {roi && (
              <WhyTrace trace={{
                source: `Real enrollment dates + monthly transaction revenue; baseline = GNN-similar non-enrolled advisors (${roi.model})`,
                computation: roi.methodology + " " + roi.caveats,
              }} />
            )}
          </CardTitle>
          {roi?.summary.avg_uplift_pp != null && (
            <Badge variant={roi.summary.avg_uplift_pp >= 0 ? "success" : "warning"}>
              avg uplift {roi.summary.avg_uplift_pp >= 0 ? "+" : ""}{roi.summary.avg_uplift_pp}pp
            </Badge>
          )}
        </CardHeader>
        <CardContent className="p-0">
          {!roi?.available ? (
            <div className="p-6 text-center text-[12px] text-muted-foreground">Computing ROI…</div>
          ) : (
            <>
              <div className="border-b px-3 py-2 text-[11px] text-muted-foreground">
                {roi.summary.enrolled_measured} enrollees measured · {roi.summary.outperforming_baseline} outperform their
                GNN-peer baseline ({roi.summary.share_outperforming_pct}%) · window {roi.window_months}mo, data through {roi.latest_data_month}
              </div>
              <div className="max-h-[300px] overflow-auto">
                <table className="w-full text-[12px]">
                  <thead className="sticky top-0 bg-white">
                    <tr className="border-b text-left text-[10px] uppercase tracking-wide text-muted-foreground">
                      <th className="px-3 py-2">Enrollee</th>
                      <th className="px-3 py-2">Cohort</th>
                      <th className="px-3 py-2 text-right">Growth</th>
                      <th className="px-3 py-2 text-right">Peer Baseline</th>
                      <th className="px-3 py-2 text-right">Uplift</th>
                    </tr>
                  </thead>
                  <tbody>
                    {roi.rows.map((r) => (
                      <tr key={r.advisor_id} className="border-b last:border-0"
                          title={`Peer baseline from: ${r.peer_group.map((p) => `${p.advisor_name} (${p.similarity})`).join(", ")}`}>
                        <td className="px-3 py-2 font-medium">{formatEntity(r.advisor_id, r.advisor_name)}</td>
                        <td className="px-3 py-2 text-muted-foreground">{r.cohort ?? "—"} · m{r.program_month ?? "—"}</td>
                        <td className="px-3 py-2 text-right font-mono">{r.growth_pct}%</td>
                        <td className="px-3 py-2 text-right font-mono text-muted-foreground">{r.peer_baseline_pct ?? "—"}%</td>
                        <td className={`px-3 py-2 text-right font-mono font-semibold ${(r.uplift_pp ?? 0) >= 0 ? "text-teal-600" : "text-red-600"}`}>
                          {r.uplift_pp == null ? "—" : `${r.uplift_pp >= 0 ? "+" : ""}${r.uplift_pp}pp`}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="px-3 py-2 text-[10px] leading-snug text-muted-foreground">{roi.caveats}</p>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
