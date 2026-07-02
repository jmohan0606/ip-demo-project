import type { Persona, ScopeType, TimePeriod } from "@/lib/types/navigation";

export type ScopeOption = {
  scopeType: ScopeType;
  scopeId: string;
  label: string;
  parentLabel?: string;
};

export type ShellContextState = {
  persona: Persona;
  scopeType: ScopeType;
  scopeId: string;
  period: TimePeriod;
  compareTo: "Prior Period" | "Prior Year" | "Peer Benchmark" | "None";
};

export type ShellContextActions = {
  setPersona: (value: Persona) => void;
  setScopeType: (value: ScopeType) => void;
  setScopeId: (value: string) => void;
  setPeriod: (value: TimePeriod) => void;
  setCompareTo: (value: ShellContextState["compareTo"]) => void;
  setLoading: (value: boolean) => void;
};

export type ShellContextValue = ShellContextState & ShellContextActions;
