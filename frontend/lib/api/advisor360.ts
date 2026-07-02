import { apiClient } from "@/lib/api/client";
import type { Advisor360Payload } from "@/lib/types/advisor360";

export async function fetchAdvisor360(advisorId = "ADV0001"): Promise<Advisor360Payload> {
  try {
    return await apiClient.post<Advisor360Payload>("/ui/advisor-360", { advisor_id: advisorId });
  } catch {
    return getMockAdvisor360(advisorId);
  }
}

export function getMockAdvisor360(advisorId: string): Advisor360Payload {
  return {
    advisorId,
    advisorName: "Avery Morgan",
    market: "Manhattan Market",
    agpStatus: "At Risk",
    revenueYtd: 4800000,
    aum: 812000000,
    nnm: 42500000,
    ncf: 18700000,
    households: [
      { householdId: "HH001", householdName: "Parker Family Trust", segment: "Ultra High Net Worth", aum: 92000000, nnm: -2200000, ncf: -950000, riskProfile: "Moderate", nextBestAction: "Managed account review" },
      { householdId: "HH002", householdName: "Rivera Household", segment: "High Net Worth", aum: 48500000, nnm: 3100000, ncf: 1200000, riskProfile: "Growth", nextBestAction: "Alternatives education" },
      { householdId: "HH003", householdName: "Chen Foundation", segment: "Institutional", aum: 111000000, nnm: 7800000, ncf: 4300000, riskProfile: "Conservative", nextBestAction: "Fixed income ladder review" }
    ],
    accounts: [
      { accountId: "ACCT001", accountType: "Managed Account", accountValue: 42000000, managed: true, productExposure: "Managed Accounts / Fixed Income" },
      { accountId: "ACCT002", accountType: "Brokerage", accountValue: 18000000, managed: false, productExposure: "Equities / Mutual Funds" },
      { accountId: "ACCT003", accountType: "IRA", accountValue: 12500000, managed: true, productExposure: "Mutual Funds / Alternatives" }
    ],
    transactions: [
      { transactionId: "TXN001", tradeDate: "2026-05-03", settlementDate: "2026-05-05", buySellFlag: "Buy", quantity: 1200, principalAmount: 1800000, revenueAmount: 18500, productCategory: "Fixed Income" },
      { transactionId: "TXN002", tradeDate: "2026-05-14", settlementDate: "2026-05-16", buySellFlag: "Sell", quantity: 400, principalAmount: 620000, revenueAmount: 7100, productCategory: "Equities" },
      { transactionId: "TXN003", tradeDate: "2026-06-02", settlementDate: "2026-06-04", buySellFlag: "Buy", quantity: 900, principalAmount: 1250000, revenueAmount: 14200, productCategory: "Managed Accounts" }
    ],
    crmActivities: [
      { activityId: "CRM001", activityType: "Meeting", activityDate: "2026-05-22", subject: "Liquidity review", outcome: "Follow-up required" },
      { activityId: "CRM002", activityType: "Call", activityDate: "2026-05-28", subject: "Portfolio review prep", outcome: "Client interested" },
      { activityId: "CRM003", activityType: "Note", activityDate: "2026-06-05", subject: "AGP coaching note", outcome: "MDW review" }
    ]
  };
}
