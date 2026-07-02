"use client";
import { useState } from "react";
import { FileText, UploadCloud, Database, CheckCircle2 } from "lucide-react";
import { useApiContextPayload } from "@/components/layout/shell-context";
import { ingestKnowledgeDocument } from "@/lib/api/integrated-ui";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { KpiCard } from "@/components/cards/kpi-card";
export function DocumentIngestionWorkspace() {
  const context = useApiContextPayload();
  const [content, setContent] = useState("Client-first conversations and aligned solutions drive higher adoption of advisory and managed offerings.");
  const [result, setResult] = useState<any | null>(null);
  async function ingest() { setResult(await ingestKnowledgeDocument(context, "advisor_playbook_demo.txt", "playbook", content)); }
  return (
    <div className="space-y-3">
      <div><Badge variant="glass">Document Ingestion Pipeline</Badge><h2 className="mt-2 text-[22px] font-black">Knowledge Documents → Chroma</h2><p className="text-[12px] text-muted-foreground">Upload, chunk, index, validate, and expose documents to AI Assistant and recommendation explainability.</p></div>
      <div className="grid gap-2 md:grid-cols-4"><KpiCard label="Documents Indexed" value="42" change="+5" icon={FileText} /><KpiCard label="Chunks" value="1,284" change="+211" icon={Database} variant="insight" /><KpiCard label="Collection" value="Ready" change="Chroma" icon={CheckCircle2} variant="insight" /><KpiCard label="Pipeline" value="Mock" change="API-backed" icon={UploadCloud} /></div>
      <Card><CardHeader className="p-3"><CardTitle className="text-[13px]">Upload / Paste Document Content</CardTitle></CardHeader><CardContent className="space-y-3 p-3"><textarea className="h-36 w-full rounded-lg border p-3 text-[12px]" value={content} onChange={(e) => setContent(e.target.value)} /><Button variant="premium" className="gap-2" onClick={ingest}><UploadCloud className="h-4 w-4" />Ingest to Chroma</Button>{result && <div className="rounded-xl border bg-good-soft p-3 text-[12px]"><strong>Indexed:</strong> {result.document_name} · {result.chunks_created} chunks · {result.chroma_collection}</div>}</CardContent></Card>
    </div>
  );
}
