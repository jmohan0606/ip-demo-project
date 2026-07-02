"use client";

import { useEffect, useState } from "react";
import { BookOpenCheck, Database, FileText, Search, UploadCloud } from "lucide-react";
import { fetchKnowledgeRuntimeStatus, ingestKnowledgeRuntime, searchKnowledgeRuntime } from "@/lib/api/knowledge-runtime";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export function KnowledgeRuntimeWorkspace() {
  const [status, setStatus] = useState<any | null>(null);
  const [query, setQuery] = useState("managed account growth playbook");
  const [content, setContent] = useState("Managed account growth requires suitability-backed reviews, recurring client meetings, household segmentation, and compliance-aware follow-up documentation.");
  const [searchResult, setSearchResult] = useState<any | null>(null);
  const [ingestResult, setIngestResult] = useState<any | null>(null);

  async function refresh() {
    setStatus(await fetchKnowledgeRuntimeStatus());
  }
  async function ingest() {
    const result = await ingestKnowledgeRuntime("advisor_growth_playbook.txt", "playbook", content, { source: "ui" });
    setIngestResult(result);
    await refresh();
  }
  async function search() {
    setSearchResult(await searchKnowledgeRuntime(query, 5));
  }

  useEffect(() => { refresh(); }, []);

  return (
    <div className="space-y-3">
      <div className="flex items-end justify-between">
        <div>
          <Badge variant="glass">Chroma & Knowledge Services</Badge>
          <h2 className="mt-2 text-[22px] font-black">Document Ingestion, Persistent Indexing & Retrieval</h2>
          <p className="text-[12px] text-muted-foreground">Chunks documents, embeds them, stores in Chroma when available, falls back to JSON vector store, and writes document lineage to graph runtime.</p>
        </div>
        <Button variant="premium" className="h-8 gap-2 text-[12px]" onClick={refresh}><Database className="h-4 w-4" />Refresh</Button>
      </div>

      <div className="grid gap-3 xl:grid-cols-3">
        <Card className={status?.active_mode === "chroma" ? "bg-good-soft" : "bg-ai-soft"}>
          <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><BookOpenCheck className="h-4 w-4" />Runtime Status</CardTitle></CardHeader>
          <CardContent className="space-y-2 p-3 text-[12px]">
            <div>Active mode: <strong>{status?.active_mode ?? status?.data?.active_mode ?? "loading"}</strong></div>
            <div>Chroma available: <strong>{String(status?.chroma_available ?? status?.data?.chroma_available)}</strong></div>
            <div>Collection: <strong>{status?.collection_name ?? status?.data?.collection_name}</strong></div>
            <div>Chunks: <strong>{status?.document_chunk_count ?? status?.data?.document_chunk_count ?? 0}</strong></div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><UploadCloud className="h-4 w-4" />Ingest Document</CardTitle></CardHeader>
          <CardContent className="space-y-3 p-3">
            <textarea className="h-28 w-full rounded-lg border p-2 text-[12px]" value={content} onChange={(e) => setContent(e.target.value)} />
            <Button className="h-8 gap-2 text-[12px]" onClick={ingest}><FileText className="h-4 w-4" />Ingest</Button>
            {ingestResult && <pre className="max-h-[180px] overflow-auto rounded-xl bg-muted p-3 text-[10px]">{JSON.stringify(ingestResult, null, 2)}</pre>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="p-3"><CardTitle className="flex items-center gap-2 text-[13px]"><Search className="h-4 w-4" />Search Knowledge</CardTitle></CardHeader>
          <CardContent className="space-y-3 p-3">
            <input className="h-8 w-full rounded-lg border px-2 text-[12px]" value={query} onChange={(e) => setQuery(e.target.value)} />
            <Button className="h-8 gap-2 text-[12px]" onClick={search}><Search className="h-4 w-4" />Search</Button>
            {searchResult && <div className="space-y-2">
              {(searchResult.data?.results ?? searchResult.results ?? []).map((r: any) => (
                <div key={`${r.title}-${r.score}`} className="rounded-xl border bg-background p-2 text-[12px]">
                  <div className="flex items-center justify-between"><strong>{r.title}</strong><Badge>{Math.round((r.score ?? 0) * 100)}%</Badge></div>
                  <p className="mt-1 text-muted-foreground">{r.snippet}</p>
                </div>
              ))}
            </div>}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
