import type { Persona, ScopeType } from "@/lib/types/navigation";
import type { ScopeOption } from "@/lib/types/shell";

export const scopeOptions: ScopeOption[] = [
  { scopeType: "Firm", scopeId: "FIRM001", label: "US Wealth Management" },
  { scopeType: "Division", scopeId: "DIV01", label: "Northeast Division", parentLabel: "US Wealth Management" },
  { scopeType: "Division", scopeId: "DIV02", label: "Central Division", parentLabel: "US Wealth Management" },
  { scopeType: "Region", scopeId: "REG0101", label: "New York Region", parentLabel: "Northeast Division" },
  { scopeType: "Region", scopeId: "REG0201", label: "Midwest Region", parentLabel: "Central Division" },
  { scopeType: "Market", scopeId: "MKT010101", label: "Manhattan Market", parentLabel: "New York Region" },
  { scopeType: "Market", scopeId: "MKT020101", label: "Chicago Market", parentLabel: "Midwest Region" },
  { scopeType: "Advisor", scopeId: "ADV0001", label: "Avery Morgan", parentLabel: "Manhattan Market" },
  { scopeType: "Advisor", scopeId: "ADV0002", label: "Jordan Patel", parentLabel: "Manhattan Market" },
  { scopeType: "Advisor", scopeId: "ADV0003", label: "Taylor Brooks", parentLabel: "Chicago Market" }
];

export const defaultScopeByPersona: Record<Persona, { scopeType: ScopeType; scopeId: string }> = {
  Firm: { scopeType: "Firm", scopeId: "FIRM001" },
  Division: { scopeType: "Division", scopeId: "DIV01" },
  Region: { scopeType: "Region", scopeId: "REG0101" },
  Market: { scopeType: "Market", scopeId: "MKT010101" },
  Advisor: { scopeType: "Advisor", scopeId: "ADV0001" },
  MDW: { scopeType: "Market", scopeId: "MKT010101" },
  DDW: { scopeType: "Division", scopeId: "DIV01" }
};

export function getScopeLabel(scopeId: string): string {
  return scopeOptions.find((item) => item.scopeId === scopeId)?.label ?? scopeId;
}

export function getAvailableScopes(scopeType?: ScopeType): ScopeOption[] {
  if (!scopeType) return scopeOptions;
  return scopeOptions.filter((item) => item.scopeType === scopeType);
}
