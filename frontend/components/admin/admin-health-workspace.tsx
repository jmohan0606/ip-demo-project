"use client";
import { Fragment, useEffect, useState } from "react";
import { Database, Network, Brain, Sparkles, CheckCircle2, AlertTriangle, Cpu } from "lucide-react";
import { fetchAdapterStatus, fetchIngestionEntityCount, type AdapterStatus } from "@/lib/api/admin";
import { apiClient } from "@/lib/api/client";
import { KpiStatCard } from "@/components/patterns/kpi-stat-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const compact = (v: number) => Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(v);

interface ModelEntry {
  name: string; version: string; algorithm: string; training_date: string; training_data?: string;
  primary_metric?: string; primary_metric_value?: number; quality_gate?: string; quality_floor?: number | null;
  features?: string[]; caveats?: string; label_definition?: string; split?: string; served_by?: string;
  metrics?: Record<string, unknown>;
}

function ModelRegistryTab() {
  const [models, setModels] = useState<ModelEntry[]>([]);
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    apiClient.get<{ models: ModelEntry[] }>("/admin/models").then((r) => setModels(r.models ?? [])).catch(() => setModels([]));
  }, []);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between p-3">
        <CardTitle className="flex items-center gap-2 text-[13px]"><Cpu className="h-4 w-4 text-primary" /> Model Registry (Section 11.1)</CardTitle>
        <span className="text-[10px] text-muted-foreground">{models.length} models · {models.filter((m) => m.quality_gate === "passed").length} serving</span>
      </CardHeader>
      <CardContent className="p-3">
        <div className="overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="border-b text-left text-[11px] uppercase text-muted-foreground">
                {["Model", "Algorithm", "Trained", "Primary metric", "Serving"].map((h) => (
                  <th key={h} className="px-2 py-1.5">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {models.map((m) => {
                const serving = m.quality_gate === "passed";
                return (
                  <Fragment key={m.name}>
                    <tr className="cursor-pointer border-b hover:bg-slate-50" onClick={() => setOpen(open === m.name ? null : m.name)}>
                      <td className="px-2 py-1.5 font-mono font-semibold">{m.name}</td>
                      <td className="px-2 py-1.5 text-muted-foreground">{m.algorithm?.split("·")[0]}</td>
                      <td className="px-2 py-1.5 font-mono">{m.training_date}</td>
                      <td className="px-2 py-1.5 font-mono">{m.primary_metric}={m.primary_metric_value}</td>
                      <td className="px-2 py-1.5"><Badge variant={serving ? "success" : "warning"}>{serving ? "serving" : "gated (fallback)"}</Badge></td>
                    </tr>
                    {open === m.name && (
                      <tr className="border-b bg-slate-50/60">
                        <td colSpan={5} className="px-3 py-2">
                          <div className="space-y-1.5 text-[12px]">
                            <div><span className="font-semibold">Algorithm:</span> {m.algorithm}</div>
                            {m.label_definition && <div><span className="font-semibold">Label:</span> {m.label_definition}</div>}
                            <div><span className="font-semibold">Training data:</span> {m.training_data}</div>
                            {m.split && <div><span className="font-semibold">Split:</span> {m.split}</div>}
                            <div><span className="font-semibold">Metrics:</span> <span className="font-mono">{JSON.stringify(m.metrics)}</span></div>
                            <div><span className="font-semibold">Features ({m.features?.length ?? 0}):</span> <span className="font-mono text-[11px]">{(m.features ?? []).join(", ")}</span></div>
                            <div className="rounded-lg border bg-amber-50 px-2 py-1 text-[11px]" style={{ borderColor: "#FDE68A", color: "#92400E" }}>
                              <span className="font-semibold">Caveats:</span> {m.caveats}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
              {models.length === 0 && <tr><td colSpan={5} className="px-2 py-3 text-center text-muted-foreground">No trained models registered. Run scripts/train/run_all.py.</td></tr>}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

function AdapterCard({
  icon,
  name,
  mode,
  healthy,
  rows,
}: {
  icon: React.ReactNode;
  name: string;
  mode: string;
  healthy?: boolean;
  rows: Array<[string, string]>;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between p-3">
        <CardTitle className="flex items-center gap-2 text-[13px]">{icon} {name}</CardTitle>
        <Badge variant={healthy === false ? "warning" : "success"}>{mode}</Badge>
      </CardHeader>
      <CardContent className="p-3">
        <dl className="divide-y rounded-xl border text-[12px]">
          {rows.map(([k, v]) => (
            <div key={k} className="flex justify-between gap-3 px-3 py-1.5">
              <dt className="text-muted-foreground">{k}</dt>
              <dd className="truncate text-right font-mono">{v}</dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  );
}

export function AdminHealthWorkspace() {
  const [status, setStatus] = useState<AdapterStatus | null>(null);
  const [entityCount, setEntityCount] = useState<number>(0);
  const [tab, setTab] = useState<"health" | "models">("health");

  useEffect(() => {
    fetchAdapterStatus().then(setStatus).catch(() => setStatus(null));
    fetchIngestionEntityCount().then(setEntityCount).catch(() => setEntityCount(0));
  }, []);

  const lr = status?.graph.load_report;
  const mismatches = lr?.row_count_mismatches.length ?? 0;
  const model = (status as unknown as { model?: { mode?: string; serving?: string[]; registered?: number }; model_client_mode?: string }) ?? {};

  return (
    <div className="space-y-3">
      <div>
        <Badge variant="glass">Admin / Data Quality / Runtime Health</Badge>
        <h2 className="mt-2 text-[22px] font-black">Runtime Adapters &amp; Data Quality</h2>
        <p className="text-[12px] text-muted-foreground">
          Live adapter modes and graph load report from `/adapters/status` — the mock/local/real
          swap-in points, with real vertex/edge row counts and load-integrity checks.
        </p>
      </div>

      <div className="flex gap-1 border-b">
        {(["health", "models"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-3 py-1.5 text-[12px] font-semibold ${tab === t ? "border-b-2 border-primary text-primary" : "text-muted-foreground"}`}>
            {t === "health" ? "System Health" : "Model Registry"}
          </button>
        ))}
      </div>

      {tab === "models" ? <ModelRegistryTab /> : (
      <div className="space-y-3">

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiStatCard label="Vertex Rows" value={lr ? compact(lr.vertex_rows) : "—"} delta={lr ? `${lr.vertex_types} types` : undefined} deltaPositive />
        <KpiStatCard label="Edge Rows" value={lr ? compact(lr.edge_rows) : "—"} delta={lr ? `${lr.edge_types} types` : undefined} deltaPositive />
        <KpiStatCard label="Row-Count Mismatches" value={String(mismatches)} delta={mismatches === 0 ? "clean" : "check"} deltaPositive={mismatches === 0} />
        <KpiStatCard label="Ingestion Entities" value={String(entityCount)} />
      </div>

      {status && (
        <div className="grid gap-3 xl:grid-cols-3">
          <AdapterCard
            icon={<Network className="h-4 w-4 text-primary" />}
            name="Graph Client"
            mode={status.graph_client_mode}
            healthy={status.graph.healthy}
            rows={[
              ["Graph", status.graph.graph],
              ["Mode", status.graph.mode],
              ["Healthy", status.graph.healthy ? "yes" : "no"],
              ["Vertex types", String(status.graph.load_report.vertex_types)],
              ["Edge types", String(status.graph.load_report.edge_types)],
            ]}
          />
          <AdapterCard
            icon={<Brain className="h-4 w-4 text-primary" />}
            name="LLM Client"
            mode={status.llm_client_mode}
            rows={[
              ["Mode", status.llm.mode],
              ["Model", status.llm.model],
              ["Anthropic key", status.anthropic_configured ? "configured" : "—"],
              ["Azure OpenAI", status.azure_openai_configured ? "configured" : "—"],
            ]}
          />
          <AdapterCard
            icon={<Sparkles className="h-4 w-4 text-primary" />}
            name="Embedding Client"
            mode={status.embedding_client_mode}
            rows={[
              ["Mode", status.embedding.mode],
              ["Model", status.embedding.model],
              ["Dimensions", String(status.embedding.dimensions)],
            ]}
          />
          <AdapterCard
            icon={<Cpu className="h-4 w-4 text-primary" />}
            name="Model Client (11.1)"
            mode={model.model_client_mode ?? "deterministic"}
            rows={[
              ["Tier", model.model?.mode ?? "—"],
              ["Registered", String(model.model?.registered ?? 0)],
              ["Serving", (model.model?.serving ?? []).join(", ") || "none"],
            ]}
          />
        </div>
      )}

      <Card>
        <CardHeader className="p-3">
          <CardTitle className="flex items-center gap-2 text-[13px]">
            <Database className="h-4 w-4 text-primary" /> Data Load Integrity
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 p-3 text-[12px]">
          <div className="flex items-center gap-2 rounded-xl border p-3">
            {mismatches === 0 ? (
              <CheckCircle2 className="h-4 w-4 text-primary" />
            ) : (
              <AlertTriangle className="h-4 w-4 text-destructive" />
            )}
            <span>
              {mismatches === 0
                ? `All ${lr?.vertex_types ?? 0} vertex types and ${lr?.edge_types ?? 0} edge types loaded with 0 row-count mismatches (${lr ? compact(lr.vertex_rows) : 0} vertices, ${lr ? compact(lr.edge_rows) : 0} edges).`
                : `${mismatches} row-count mismatch(es) detected against manifest expectations.`}
            </span>
          </div>
        </CardContent>
      </Card>
      </div>
      )}
    </div>
  );
}
