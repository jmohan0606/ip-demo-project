import { Badge } from "@/components/ui/badge";

export function StatusPill({ status }: { status?: string }) {
  const normalized = (status ?? "good").toLowerCase();
  if (["bad", "critical", "blocked", "high"].includes(normalized)) return <Badge variant="destructive">{status}</Badge>;
  if (["warn", "warning", "medium", "review required", "at risk"].includes(normalized)) return <Badge variant="warning">{status}</Badge>;
  return <Badge variant="success">{status}</Badge>;
}
