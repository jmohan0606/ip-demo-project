import type { GraphExplorerPayload } from "@/lib/types/graph_explorer";

export async function fetchGraphExplorerData(): Promise<GraphExplorerPayload> {
  return {
    nodes: [
      { id: "ADV0001", label: "Avery Morgan", type: "Advisor", score: 0.88, description: "Advisor in AGP, revenue up, NNM watchlist." },
      { id: "HH001", label: "Parker Family Trust", type: "Household", score: 0.91, description: "High AUM household with managed account opportunity." },
      { id: "ACCT001", label: "Managed Account", type: "Account", score: 0.74 },
      { id: "PROD001", label: "Managed Accounts", type: "Product", score: 0.84 },
      { id: "OPP001", label: "Managed Account Expansion", type: "Opportunity", score: 0.91 },
      { id: "REC001", label: "Schedule Review", type: "Recommendation", score: 0.88 },
      { id: "MEM001", label: "Advisor Memory", type: "Memory", score: 0.86 },
      { id: "TXN001", label: "Fixed Income Buy", type: "Transaction", score: 0.72 }
    ],
    edges: [
      { id: "e1", source: "ADV0001", target: "HH001", label: "SERVES", weight: 0.95 },
      { id: "e2", source: "HH001", target: "ACCT001", label: "OWNS", weight: 0.9 },
      { id: "e3", source: "ACCT001", target: "PROD001", label: "HOLDS", weight: 0.82 },
      { id: "e4", source: "HH001", target: "OPP001", label: "HAS_OPPORTUNITY", weight: 0.91 },
      { id: "e5", source: "OPP001", target: "REC001", label: "GENERATES", weight: 0.88 },
      { id: "e6", source: "ADV0001", target: "MEM001", label: "HAS_MEMORY", weight: 0.86 },
      { id: "e7", source: "ACCT001", target: "TXN001", label: "HAS_TRANSACTION", weight: 0.72 }
    ]
  };
}
