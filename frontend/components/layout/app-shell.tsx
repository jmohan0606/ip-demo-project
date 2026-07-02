"use client";
import { ReactNode, useMemo, useState } from "react";
import { SidebarNavigation } from "@/components/navigation/sidebar-navigation";
import { TopHeader } from "@/components/layout/top-header";
import { ShellContext } from "@/components/layout/shell-context";
import { GlobalLoadingOverlay } from "@/components/loading/global-loading-overlay";
import type { Persona, ScopeType, TimePeriod } from "@/lib/types/navigation";
import type { ShellContextState } from "@/lib/types/shell";
import { defaultScopeByPersona } from "@/lib/scope-options";

export function AppShell({ children }: { children: ReactNode }) {
  const [persona, setPersonaState] = useState<Persona>("Advisor");
  const [scopeType, setScopeType] = useState<ScopeType>("Advisor");
  const [scopeId, setScopeId] = useState("ADV0001");
  const [period, setPeriod] = useState<TimePeriod>("YTD");
  const [compareTo, setCompareTo] = useState<ShellContextState["compareTo"]>("Prior Year");
  const [loading, setLoading] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  function setPersona(value: Persona) {
    setPersonaState(value);
    const nextScope = defaultScopeByPersona[value];
    setScopeType(nextScope.scopeType);
    setScopeId(nextScope.scopeId);
  }
  const context = useMemo(() => ({ persona, scopeType, scopeId, period, compareTo, setPersona, setScopeType, setScopeId, setPeriod, setCompareTo, setLoading }), [persona, scopeType, scopeId, period, compareTo]);

  return (
    <ShellContext.Provider value={context}>
      <div className="compact-shell enterprise-shell-bg min-h-screen">
        <GlobalLoadingOverlay active={loading} message="Loading iPerform intelligence..." />
        <div className="flex min-h-screen">
          <SidebarNavigation collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed((v) => !v)} />
          <div className="flex min-w-0 flex-1 flex-col">
            <TopHeader />
            <main className="flex-1 px-3 py-3 xl:px-4">{children}</main>
          </div>
        </div>
      </div>
    </ShellContext.Provider>
  );
}
