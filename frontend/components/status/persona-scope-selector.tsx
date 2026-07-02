"use client";
import { useMemo } from "react";
import { useShellContext } from "@/components/layout/shell-context";
import type { Persona, ScopeType, TimePeriod } from "@/lib/types/navigation";
import { getAvailableScopes } from "@/lib/scope-options";
const personas: Persona[] = ["Firm", "Division", "Region", "Market", "Advisor", "MDW", "DDW"];
const scopeTypes: ScopeType[] = ["Firm", "Division", "Region", "Market", "Advisor"];
const periods: TimePeriod[] = ["MTD", "QTD", "YTD", "LTM", "Custom"];
const compareOptions = ["Prior Period", "Prior Year", "Peer Benchmark", "None"] as const;
export function PersonaScopeSelector() {
  const context = useShellContext();
  const scopes = useMemo(() => getAvailableScopes(context.scopeType), [context.scopeType]);
  const cls = "h-8 rounded-lg border border-border bg-background px-2 text-[12px] font-semibold";
  return (
    <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
      <select className={cls} value={context.persona} onChange={(event) => context.setPersona(event.target.value as Persona)}>{personas.map((value) => <option key={value}>{value}</option>)}</select>
      <select className={cls} value={context.scopeType} onChange={(event) => context.setScopeType(event.target.value as ScopeType)}>{scopeTypes.map((value) => <option key={value}>{value}</option>)}</select>
      <select className={cls} value={context.scopeId} onChange={(event) => context.setScopeId(event.target.value)}>{scopes.map((scope) => <option key={scope.scopeId} value={scope.scopeId}>{scope.label}</option>)}</select>
      <select className={cls} value={context.period} onChange={(event) => context.setPeriod(event.target.value as TimePeriod)}>{periods.map((value) => <option key={value}>{value}</option>)}</select>
      <select className={cls} value={context.compareTo} onChange={(event) => context.setCompareTo(event.target.value as typeof compareOptions[number])}>{compareOptions.map((value) => <option key={value}>{value}</option>)}</select>
    </div>
  );
}
