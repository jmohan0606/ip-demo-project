export type Persona = "Firm" | "Division" | "Region" | "Market" | "Advisor" | "MDW" | "DDW";
export type ScopeType = "Firm" | "Division" | "Region" | "Market" | "Advisor";
export type TimePeriod = "MTD" | "QTD" | "YTD" | "LTM" | "Custom";
export type NavigationItem = {
  id: string;
  label: string;
  description: string;
  href: string;
  iconName: string;
  group: "Executive" | "Advisor" | "AI" | "Graph" | "Operations" | "Admin";
  status?: "ready" | "new" | "audit";
};
