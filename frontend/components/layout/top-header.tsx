"use client";
import { RefreshCcw, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { useShellContext } from "@/components/layout/shell-context";
import { PersonaScopeSelector } from "@/components/status/persona-scope-selector";
import { SystemStatusPill } from "@/components/status/system-status-pill";

export function TopHeader() {
  const ctx = useShellContext();
  const router = useRouter();
  return (
    <header className="sticky top-0 z-30 border-b border-border/60 bg-background/85 px-3 py-2 backdrop-blur-xl xl:px-4">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <h1 className="truncate text-[20px] font-black tracking-tight">Advisor Revenue Intelligence & AI Coaching Copilot</h1>
          <p className="text-[12px] text-muted-foreground">Real-time revenue insights, predictions, recommendations & learning</p>
        </div>
        <div className="flex items-center gap-2">
          <SystemStatusPill />
          {/* Refresh = re-fetch the current page's data without losing scope. */}
          <Button variant="outline" size="sm" className="h-8 gap-1 text-[12px]" onClick={() => ctx.refresh()} title="Re-fetch this page's data">
            <RefreshCcw className="h-3.5 w-3.5" />Refresh
          </Button>
          {/* Search = the real RAG knowledge search page. */}
          <Button variant="outline" size="icon" className="h-8 w-8" onClick={() => router.push("/knowledge")} title="Search the knowledge base">
            <Search className="h-3.5 w-3.5" />
          </Button>
          {/* Bell/alerts removed: no notifications backend exists — no decorative dead buttons (9.2). */}
        </div>
      </div>
      <div className="mt-2"><PersonaScopeSelector /></div>
    </header>
  );
}
