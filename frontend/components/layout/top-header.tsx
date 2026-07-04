"use client";
import { Bell, RefreshCcw, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PersonaScopeSelector } from "@/components/status/persona-scope-selector";
import { SystemStatusPill } from "@/components/status/system-status-pill";

export function TopHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-border/60 bg-background/85 px-3 py-2 backdrop-blur-xl xl:px-4">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <h1 className="truncate text-[20px] font-black tracking-tight">Advisor Revenue Intelligence & AI Coaching Copilot</h1>
          <p className="text-[12px] text-muted-foreground">Real-time revenue insights, predictions, recommendations & learning</p>
        </div>
        <div className="flex items-center gap-2">
          <SystemStatusPill />
          <Button variant="outline" size="sm" className="h-8 gap-1 text-[12px]"><RefreshCcw className="h-3.5 w-3.5" />Refresh</Button>
          <Button variant="outline" size="icon" className="h-8 w-8"><Search className="h-3.5 w-3.5" /></Button>
          <Button variant="outline" size="icon" className="h-8 w-8"><Bell className="h-3.5 w-3.5" /></Button>
        </div>
      </div>
      <div className="mt-2"><PersonaScopeSelector /></div>
    </header>
  );
}
