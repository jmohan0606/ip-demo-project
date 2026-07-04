"use client";
import { useCallback, useEffect, useState } from "react";
import { PlayCircle, Sparkles } from "lucide-react";
import { useShellContext } from "@/components/layout/shell-context";
import { apiClient } from "@/lib/api/client";
import { resolveScope } from "@/lib/api/hierarchy";
import { simulateWhatIf, type WhatIfLevers, type WhatIfResult } from "@/lib/api/whatif";
import { AssumptionSlider } from "@/components/whatif/assumption-slider";
import { WhatIfImpactBars } from "@/components/charts/whatif-impact-bars";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { formatCurrency } from "@/lib/utils";

const DEFAULT_LEVERS: WhatIfLevers = {
  meeting_increase_pct: 20,
  prospecting_increase_pct: 10,
  aum_growth_pct: 5,
  goal_reviews_added: 2,
  horizon_months: 6,
};

function fmt(unit: string, value: number) {
  return unit === "USD" ? formatCurrency(value) : `${value.toFixed(1)} pts`;
}

export function WhatIfSimulatorClient() {
  const shell = useShellContext();
  const [advisors, setAdvisors] = useState<Array<{ advisor_id: string; advisor_name: string | null }>>([]);
  // The simulator follows the shell scope: an Advisor scope pins that advisor,
  // a rollup scope (Firm/Division/…) falls back to the first advisor beneath it.
  const [advisorId, setAdvisorId] = useState("A001");
  const [levers, setLevers] = useState<WhatIfLevers>(DEFAULT_LEVERS);
  const [result, setResult] = useState<WhatIfResult | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    apiClient
      .get<{ advisors: Array<{ advisor_id: string; advisor_name: string | null }> }>("/advisor/list")
      .then((r) => setAdvisors(r.advisors))
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

  const update = (key: keyof WhatIfLevers, value: number) =>
    setLevers((current) => ({ ...current, [key]: value }));

  const run = useCallback(async () => {
    setBusy(true);
    try {
      setResult(await simulateWhatIf(advisorId, levers));
    } finally {
      setBusy(false);
    }
  }, [advisorId, levers]);

  const advisorName =
    advisors.find((a) => a.advisor_id === advisorId)?.advisor_name ?? advisorId;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <Badge variant="glass">Scenario Simulator</Badge>
          <h2 className="mt-2 text-[22px] font-black">What-If Scenario Simulator</h2>
          <p className="text-[12px] text-muted-foreground">
            Projects <strong>{advisorName}</strong>&apos;s real current feature snapshot forward under the
            scenario levers — transparent elasticity formulas, not fabricated figures.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            className="h-8 rounded-lg border border-border bg-background px-2 text-[12px]"
            value={advisorId}
            onChange={(e) => setAdvisorId(e.target.value)}
          >
            {advisors.length === 0 && <option value={advisorId}>{advisorId}</option>}
            {advisors.map((a) => (
              <option key={a.advisor_id} value={a.advisor_id}>
                {a.advisor_name ?? a.advisor_id}
              </option>
            ))}
          </select>
          <Button variant="premium" className="h-8 gap-2 text-[12px]" onClick={run} disabled={busy}>
            <PlayCircle className="h-4 w-4" />
            {busy ? "Running…" : "Run Scenario"}
          </Button>
        </div>
      </div>

      <div className="grid gap-3 xl:grid-cols-[.9fr_1.1fr]">
        <Card>
          <CardHeader className="p-3">
            <CardTitle className="text-[13px]">Scenario Levers</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 p-3">
            <AssumptionSlider
              label="Client Meeting Frequency"
              value={levers.meeting_increase_pct}
              onChange={(v) => update("meeting_increase_pct", v)}
            />
            <AssumptionSlider
              label="Prospecting Activity"
              value={levers.prospecting_increase_pct}
              onChange={(v) => update("prospecting_increase_pct", v)}
            />
            <AssumptionSlider
              label="AUM Growth"
              value={levers.aum_growth_pct}
              onChange={(v) => update("aum_growth_pct", v)}
            />
            <AssumptionSlider
              label="Added Goal Reviews"
              value={levers.goal_reviews_added}
              onChange={(v) => update("goal_reviews_added", v)}
              min={0}
              max={12}
              suffix=""
            />
            <AssumptionSlider
              label="Horizon"
              value={levers.horizon_months}
              onChange={(v) => update("horizon_months", v)}
              min={1}
              max={24}
              suffix=" mo"
            />
          </CardContent>
        </Card>

        <Card className="bg-ai-soft">
          <CardHeader className="flex flex-row items-center justify-between p-3">
            <CardTitle className="text-[13px]">Projected Impact</CardTitle>
            {result && (
              <Badge variant="glass" className="gap-1 text-[10px]">
                <Sparkles className="h-3 w-3" /> {result.horizon_months}-month projection
              </Badge>
            )}
          </CardHeader>
          <CardContent className="space-y-3 p-3">
            {!result ? (
              <div className="rounded-xl border border-dashed p-8 text-center text-muted-foreground">
                Run the scenario to project {advisorName}&apos;s real snapshot forward.
              </div>
            ) : (
              <>
                <div className="rounded-xl border bg-background/80 p-2">
                  <WhatIfImpactBars data={result.metrics} />
                </div>
                <div className="space-y-2">
                  {result.metrics.map((m) => {
                    const up = m.change >= 0;
                    return (
                      <div key={m.metric} className="rounded-xl border bg-background/80 p-3 text-[12px]">
                        <div className="flex items-center justify-between">
                          <div className="font-bold uppercase tracking-wide">{m.metric}</div>
                          <Badge variant={up ? "success" : "destructive"}>
                            {up ? "+" : ""}
                            {fmt(m.unit, m.change)}
                            {m.change_pct !== null && ` (${up ? "+" : ""}${m.change_pct.toFixed(1)}%)`}
                          </Badge>
                        </div>
                        <div className="mt-1 flex gap-6 text-muted-foreground">
                          <span>
                            Current <strong className="text-foreground">{fmt(m.unit, m.current)}</strong>
                          </span>
                          <span>
                            Projected <strong className="text-foreground">{fmt(m.unit, m.projected)}</strong>
                          </span>
                        </div>
                        <div className="mt-1 truncate font-mono text-[10px] text-muted-foreground" title={m.formula}>
                          ƒ {m.formula}
                        </div>
                      </div>
                    );
                  })}
                </div>
                <div className="rounded-xl border bg-good-soft p-3 text-[11px] text-muted-foreground">
                  <span className="font-semibold text-foreground">Evidence · </span>
                  {result.note} Baseline snapshot{" "}
                  <span className="font-mono">{result.snapshot_id ?? "computed on-the-fly"}</span> ·
                  revenue_ltm {formatCurrency(result.baseline_features.revenue_ltm)} · aum_total{" "}
                  {formatCurrency(result.baseline_features.aum_total)}.
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
