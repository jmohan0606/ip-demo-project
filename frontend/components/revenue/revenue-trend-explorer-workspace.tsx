"use client";

import { useShellContext } from "@/components/layout/shell-context";
import RevenueTrendExplorer from "@/components/revenue/revenue-trend-explorer";
import { Badge } from "@/components/ui/badge";
import { type } from "@/styles/tokens";

export function RevenueTrendExplorerWorkspace() {
  const shell = useShellContext();

  return (
    <div className="space-y-3">
      <div>
        <Badge variant="glass">Revenue Intelligence</Badge>
        <h2 className={`mt-2 ${type.pageTitle}`}>Revenue Trend Explorer</h2>
        <p className="text-[12px] text-muted-foreground">
          {shell.scopeType} scope · {shell.scopeLabel || shell.scopeId} — revenue per period sliced by a
          selectable dimension, with AI-summarized drivers per period. Click a bar to inspect that period.
        </p>
      </div>
      <RevenueTrendExplorer />
    </div>
  );
}
