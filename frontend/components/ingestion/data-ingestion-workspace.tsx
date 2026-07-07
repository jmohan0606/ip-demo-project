"use client";
import { type } from "@/styles/tokens";
import { useEffect, useMemo, useState } from "react";
import { Database, PlayCircle, GitBranch, Layers, CheckCircle2, AlertTriangle } from "lucide-react";
import {
  fetchIngestionEntities,
  fetchManifest,
  runIngestion,
  type IngestionEntity,
  type IngestionBatchStatus,
  type ManifestSummary,
} from "@/lib/api/ingestion";
import { KpiStatCard } from "@/components/patterns/kpi-stat-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const STATUS_VARIANT: Record<string, "success" | "warning" | "destructive" | "glass"> = {
  completed: "success",
  running: "warning",
  failed: "destructive",
  pending: "glass",
};

export function DataIngestionWorkspace() {
  const [entities, setEntities] = useState<IngestionEntity[]>([]);
  const [manifest, setManifest] = useState<ManifestSummary | null>(null);
  const [selected, setSelected] = useState<string>("feature_snapshot");
  const [batch, setBatch] = useState<IngestionBatchStatus | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetchIngestionEntities().then(setEntities).catch(() => setEntities([]));
    fetchManifest().then(setManifest).catch(() => setManifest(null));
  }, []);

  const kpis = useMemo(() => {
    const vertices = new Set(entities.map((e) => e.tigergraph_vertex));
    const edgeFiles = entities.reduce((s, e) => s + e.edge_files.length, 0);
    const columns = entities.reduce((s, e) => s + e.required_columns.length, 0);
    return { entities: entities.length, vertices: vertices.size, edgeFiles, columns };
  }, [entities]);

  async function run() {
    setBusy(true);
    try {
      const r = await runIngestion(selected);
      setBatch(r.batch_status);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <Badge variant="glass">Data Ingestion &amp; Sync</Badge>
          <h2 className={`mt-2 ${type.pageTitle}`}>Manifest-Driven Ingestion &amp; Checkpointing</h2>
          <p className="text-[12px] text-muted-foreground">
            Real entity manifest from the foundation package — upsert with batch/checkpoint/retry.
            {manifest && ` Graph ${manifest.graph_name} · stage ${manifest.package_stage} · ${manifest.foundation_status}.`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            className="h-8 rounded-lg border border-border bg-background px-2 text-[12px]"
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
          >
            {entities.map((e) => (
              <option key={e.entity_name} value={e.entity_name}>{e.entity_name}</option>
            ))}
          </select>
          <Button variant="premium" className="h-8 gap-2 text-[12px]" onClick={run} disabled={busy}>
            <PlayCircle className="h-4 w-4" /> {busy ? "Running…" : "Run Ingestion"}
          </Button>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiStatCard label="Configured Entities" value={String(kpis.entities)} />
        <KpiStatCard label="Graph Vertices" value={String(kpis.vertices)} />
        <KpiStatCard label="Edge Files" value={String(kpis.edgeFiles)} />
        <KpiStatCard label="Required Columns" value={String(kpis.columns)} />
      </div>

      {batch && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between p-3">
            <CardTitle className="flex items-center gap-2 text-[13px]">
              {batch.status === "failed" ? (
                <AlertTriangle className="h-4 w-4 text-destructive" />
              ) : (
                <CheckCircle2 className="h-4 w-4 text-primary" />
              )}
              Last Run · {batch.entity_name} ({batch.file_name})
            </CardTitle>
            <Badge variant={STATUS_VARIANT[batch.status] ?? "glass"}>{batch.status}</Badge>
          </CardHeader>
          <CardContent className="space-y-2 p-3">
            <div className="grid grid-cols-2 gap-2 text-[12px] sm:grid-cols-4">
              <Stat label="Total" value={batch.total_records} />
              <Stat label="Processed" value={batch.processed_records} />
              <Stat label="Created" value={batch.created_records} />
              <Stat label="Updated" value={batch.updated_records} />
              <Stat label="Skipped" value={batch.skipped_records} />
              <Stat label="Failed" value={batch.failed_records} />
              <Stat label="Last Row" value={batch.last_processed_row} />
              <Stat label="Progress" value={`${batch.progress_percent.toFixed(0)}%`} />
            </div>
            {batch.message && (
              <div className="rounded-lg border bg-muted/40 px-3 py-2 font-mono text-[11px] text-muted-foreground">
                {batch.message} · checkpoint {batch.batch_id}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="p-3">
          <CardTitle className="flex items-center gap-2 text-[13px]">
            <Database className="h-4 w-4 text-primary" /> Entity Manifest ({entities.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-[12px]">
              <thead>
                <tr className="border-b text-left text-[10px] uppercase tracking-wide text-muted-foreground">
                  <th className="px-3 py-2">Entity</th>
                  <th className="px-3 py-2">CSV</th>
                  <th className="px-3 py-2">Vertex</th>
                  <th className="px-3 py-2">PK</th>
                  <th className="px-3 py-2 text-right">Cols</th>
                  <th className="px-3 py-2 text-right">Edges</th>
                  <th className="px-3 py-2 text-right">Batch</th>
                </tr>
              </thead>
              <tbody>
                {entities.map((e) => (
                  <tr
                    key={e.entity_name}
                    className={`cursor-pointer border-b last:border-0 hover:bg-muted/40 ${selected === e.entity_name ? "bg-muted/40" : ""}`}
                    onClick={() => setSelected(e.entity_name)}
                  >
                    <td className="px-3 py-2 font-medium">{e.entity_name}</td>
                    <td className="px-3 py-2 font-mono text-[11px] text-muted-foreground">{e.csv_file_name}</td>
                    <td className="px-3 py-2 font-mono text-[11px]">{e.tigergraph_vertex}</td>
                    <td className="px-3 py-2 font-mono text-[11px] text-muted-foreground">{e.primary_key}</td>
                    <td className="px-3 py-2 text-right">{e.required_columns.length}</td>
                    <td className="px-3 py-2 text-right">
                      <span className="inline-flex items-center gap-1">
                        <GitBranch className="h-3 w-3 text-muted-foreground" />
                        {e.edge_files.length}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right font-mono">{e.batch_size}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {manifest && (
        <Card>
          <CardHeader className="p-3">
            <CardTitle className="flex items-center gap-2 text-[13px]">
              <Layers className="h-4 w-4 text-primary" /> Foundation Capabilities Locked
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-1.5 p-3">
            {manifest.capabilities_locked.map((c) => (
              <Badge key={c} variant="glass" className="text-[10px]">{c}</Badge>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-lg border bg-background/70 px-3 py-2">
      <div className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="font-mono text-[15px] font-bold">{value}</div>
    </div>
  );
}
