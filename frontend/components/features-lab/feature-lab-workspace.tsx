"use client";

import { useCallback, useEffect, useState } from "react";

import { EmbeddingScatter, type ProjectionPoint } from "@/components/charts/embedding-scatter";
import { KpiStatCard } from "@/components/patterns/kpi-stat-card";
import { apiClient } from "@/lib/api/client";
import { useScopedAdvisor } from "@/lib/hooks/use-scoped-advisor";
import { colors, type } from "@/styles/tokens";

interface Projection {
  advisor_id: string;
  source_dimensions: number;
  reduction: string;
  explained_variance_ratio: number[];
  point_count: number;
  points: ProjectionPoint[];
}

interface Snapshot {
  snapshot_id: string;
  entity_id: string;
  snapshot_time: string;
  feature_version: string;
  features: Record<string, number | string | null>;
  lineage: Record<string, { group: string; source: string; evidence: Record<string, unknown> }>;
}

interface SimilarResponse {
  advisor_id: string;
  model: string;
  version: string;
  matches: Array<{ target_entity_id: string; similarity_score: number; reason_features: string[] }>;
  simulation_note: string;
}

export function FeatureLabWorkspace() {
  const { advisorId, refreshNonce } = useScopedAdvisor();
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [similar, setSimilar] = useState<SimilarResponse | null>(null);
  const [projection, setProjection] = useState<Projection | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!advisorId) return;
    setBusy(true);
    try {
      const snap = await apiClient.get<Snapshot | null>(`/features/snapshot/${advisorId}`);
      setSnapshot(snap);
      setSimilar(await apiClient.get<SimilarResponse>(`/embeddings/similar/${advisorId}`).catch(() => null));
      setProjection(await apiClient.get<Projection>(`/embeddings/projection/${advisorId}`).catch(() => null));
    } finally {
      setBusy(false);
    }
  }, [advisorId, refreshNonce]);

  useEffect(() => {
    void load();
  }, [load]);

  const compute = async () => {
    if (!advisorId) return;
    setBusy(true);
    try {
      await apiClient.post(`/features/compute/${advisorId}`);
      await load();
    } finally {
      setBusy(false);
    }
  };

  const featureNames = snapshot ? Object.keys(snapshot.features) : [];
  const groups = snapshot
    ? Array.from(new Set(featureNames.map((name) => snapshot.lineage[name]?.group ?? "Other")))
    : [];

  return (
    <div className="space-y-4 p-6" style={{ backgroundColor: colors.surface.canvas, minHeight: "100vh" }}>
      <div className="flex items-center justify-between">
        <div>
          <h1 className={type.pageTitle} style={{ color: colors.text.primary }}>Feature Engineering Lab</h1>
          <p className={type.body} style={{ color: colors.text.secondary }}>
            Versioned feature snapshot for {advisorId}, with per-feature lineage back to the graph queries
            and evidence that produced each value.
          </p>
        </div>
        <button
          onClick={() => void compute()}
          disabled={busy}
          className="rounded-lg px-3 py-1.5 text-[13px] font-semibold text-white disabled:opacity-50"
          style={{ backgroundColor: colors.primary }}
        >
          {busy ? "Working…" : "Recompute snapshot"}
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <KpiStatCard label="Snapshot" value={snapshot?.snapshot_id.slice(0, 16) ?? "—"} />
        <KpiStatCard label="Feature count" value={String(featureNames.length)} />
        <KpiStatCard label="Version" value={snapshot?.feature_version ?? "—"} />
        <KpiStatCard label="As of" value={snapshot?.snapshot_time ?? "—"} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2 rounded-xl border bg-white p-4 shadow-sm" style={{ borderColor: colors.surface.border }}>
          <h2 className={type.cardTitle} style={{ color: colors.text.primary }}>Embedding projection</h2>
          <p className={type.data} style={{ color: colors.text.muted }}>
            Every point is a real advisor embedding vector projected to 2D — {advisorId} and its
            nearest cohort stand out from the book.
          </p>
          {projection && projection.points.length ? (
            <div className="mt-2">
              <EmbeddingScatter points={projection.points} explainedVariance={projection.explained_variance_ratio} />
            </div>
          ) : (
            <div className="mt-2 h-[300px] animate-pulse rounded-lg bg-slate-100" />
          )}
        </div>

        <div className="rounded-xl border bg-white p-4 shadow-sm" style={{ borderColor: colors.surface.border }}>
          <h2 className={type.cardTitle} style={{ color: colors.text.primary }}>Similar advisors</h2>
          <p className={type.data} style={{ color: colors.text.muted }}>
            {similar?.simulation_note ?? "Cosine similarity over the deterministic feature projection."}
          </p>
          <div className="mt-2 space-y-1.5">
            {(similar?.matches ?? []).map((match) => (
              <div
                key={match.target_entity_id}
                className="flex items-center justify-between rounded-lg border px-2.5 py-1.5"
                style={{ borderColor: colors.surface.border }}
              >
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full" style={{ backgroundColor: colors.warning }} />
                  <span className={`font-mono ${type.data}`} style={{ color: colors.text.primary }}>
                    {match.target_entity_id}
                  </span>
                </span>
                <span className={type.data} style={{ color: colors.text.muted }}>
                  {match.reason_features.slice(0, 2).join(", ")}
                </span>
                <span className="font-mono text-[12px] font-bold" style={{ color: colors.primary }}>
                  {match.similarity_score.toFixed(3)}
                </span>
              </div>
            ))}
            {!similar?.matches?.length ? (
              <p className={type.data} style={{ color: colors.text.muted }}>
                No matches yet — run POST /embeddings/build.
              </p>
            ) : null}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2 rounded-xl border bg-white shadow-sm" style={{ borderColor: colors.surface.border }}>
          <table className="w-full">
            <thead>
              <tr className="border-b text-left" style={{ borderColor: colors.surface.border }}>
                <th className={`px-3 py-2 ${type.label}`} style={{ color: colors.text.muted }}>Feature</th>
                <th className={`px-3 py-2 ${type.label}`} style={{ color: colors.text.muted }}>Group</th>
                <th className={`px-3 py-2 text-right ${type.label}`} style={{ color: colors.text.muted }}>Value</th>
              </tr>
            </thead>
            <tbody>
              {groups.map((group) => (
                featureNames
                  .filter((name) => (snapshot!.lineage[name]?.group ?? "Other") === group)
                  .map((name) => (
                    <tr
                      key={name}
                      onClick={() => setSelected(name)}
                      className="cursor-pointer border-b last:border-0 hover:bg-slate-50"
                      style={{
                        borderColor: colors.surface.border,
                        backgroundColor: selected === name ? "#EFF6FF" : undefined,
                      }}
                    >
                      <td className={`px-3 py-1.5 font-mono ${type.data}`} style={{ color: colors.text.primary }}>{name}</td>
                      <td className={`px-3 py-1.5 ${type.data}`} style={{ color: colors.text.muted }}>{group}</td>
                      <td className={`px-3 py-1.5 text-right font-mono ${type.data}`} style={{ color: colors.text.primary }}>
                        {snapshot!.features[name] === null ? "—" : String(snapshot!.features[name])}
                      </td>
                    </tr>
                  ))
              ))}
            </tbody>
          </table>
        </div>

        <div className="space-y-4">
          <div className="rounded-xl border bg-white p-4 shadow-sm" style={{ borderColor: colors.surface.border }}>
            <h2 className={type.cardTitle} style={{ color: colors.text.primary }}>Lineage</h2>
            {selected && snapshot ? (
              <div className="mt-2 space-y-2">
                <p className={`font-mono ${type.data}`} style={{ color: colors.aiAccent }}>{selected}</p>
                <p className={type.data} style={{ color: colors.text.secondary }}>
                  Source: {snapshot.lineage[selected]?.source}
                </p>
                <pre
                  className="max-h-64 overflow-auto rounded-lg border p-2 font-mono text-[10px] leading-4"
                  style={{ borderColor: colors.surface.border, backgroundColor: colors.surface.canvas, color: colors.text.secondary }}
                >
                  {JSON.stringify(snapshot.lineage[selected]?.evidence, null, 2)}
                </pre>
              </div>
            ) : (
              <p className={`mt-2 ${type.data}`} style={{ color: colors.text.muted }}>
                Select a feature row to inspect which query and evidence produced its value.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
