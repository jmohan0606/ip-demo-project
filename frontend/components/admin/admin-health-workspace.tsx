"use client";
import { useEffect, useState } from "react";
import { Database, Network, Brain, Sparkles, CheckCircle2, AlertTriangle } from "lucide-react";
import { fetchAdapterStatus, fetchIngestionEntityCount, type AdapterStatus } from "@/lib/api/admin";
import { KpiStatCard } from "@/components/patterns/kpi-stat-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const compact = (v: number) => Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(v);

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

  useEffect(() => {
    fetchAdapterStatus().then(setStatus).catch(() => setStatus(null));
    fetchIngestionEntityCount().then(setEntityCount).catch(() => setEntityCount(0));
  }, []);

  const lr = status?.graph.load_report;
  const mismatches = lr?.row_count_mismatches.length ?? 0;

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
  );
}
