import { apiClient } from "@/lib/api/client";
import type { ExecutiveDashboardPayload } from "@/lib/types/dashboard";

export async function fetchExecutiveDashboard(): Promise<ExecutiveDashboardPayload> {
  try {
    // This endpoint can be added later; fallback keeps UI usable during frontend build.
    return await apiClient.post<ExecutiveDashboardPayload>("/ui/executive-dashboard", {});
  } catch {
    return getMockExecutiveDashboard();
  }
}

export function getMockExecutiveDashboard(): ExecutiveDashboardPayload {
  return {
    scopeLabel: "Advisor / Avery Morgan",
    periodLabel: "YTD vs Peer Benchmark",
    kpis: [
      { id: "revenue", label: "Revenue YTD", value: "$4.8M", change: "+8.2%", trend: "up", description: "Above prior period but below top-quartile peer group.", tone: "default" },
      { id: "aum", label: "AUM", value: "$812M", change: "+5.4%", trend: "up", description: "Positive AUM movement with concentration in managed accounts.", tone: "insight" },
      { id: "nnm", label: "NNM", value: "$42.5M", change: "-2.1%", trend: "down", description: "Net new money pressure in two large households.", tone: "risk" },
      { id: "ncf", label: "NCF", value: "$18.7M", change: "+3.6%", trend: "up", description: "Net cash flow improved after recent household engagement.", tone: "default" }
    ],
    performanceTrend: [
      { period: "Jan", revenue: 330000, aum: 760000000, nnm: 3200000, ncf: 1500000 },
      { period: "Feb", revenue: 360000, aum: 771000000, nnm: 4100000, ncf: 1800000 },
      { period: "Mar", revenue: 390000, aum: 782000000, nnm: 2600000, ncf: 1400000 },
      { period: "Apr", revenue: 410000, aum: 795000000, nnm: 5200000, ncf: 2100000 },
      { period: "May", revenue: 435000, aum: 804000000, nnm: 3800000, ncf: 1900000 },
      { period: "Jun", revenue: 462000, aum: 812000000, nnm: 2900000, ncf: 2200000 }
    ],
    productMix: [
      { category: "Managed Accounts", revenue: 1850000, growth: 9.4, share: 38 },
      { category: "Brokerage", revenue: 1210000, growth: -3.1, share: 25 },
      { category: "Fixed Income", revenue: 760000, growth: 5.6, share: 16 },
      { category: "Mutual Funds", revenue: 520000, growth: 2.2, share: 11 },
      { category: "Alternatives", revenue: 310000, growth: 12.7, share: 6 },
      { category: "Other", revenue: 190000, growth: 1.4, share: 4 }
    ],
    topPerformers: [
      { rank: 1, advisorId: "ADV0032", advisorName: "Maya Chen", market: "Manhattan", revenue: 7350000, growth: 18.4, agpStatus: "Not AGP" },
      { rank: 2, advisorId: "ADV0019", advisorName: "Noah Williams", market: "Chicago", revenue: 6840000, growth: 15.2, agpStatus: "On Track" },
      { rank: 3, advisorId: "ADV0001", advisorName: "Avery Morgan", market: "Manhattan", revenue: 4800000, growth: 8.2, agpStatus: "At Risk" }
    ],
    bottomPerformers: [
      { rank: 1, advisorId: "ADV0027", advisorName: "Riley Thomas", market: "Chicago", revenue: 940000, growth: -11.6, agpStatus: "Off Track" },
      { rank: 2, advisorId: "ADV0011", advisorName: "Casey Miller", market: "Manhattan", revenue: 1120000, growth: -8.5, agpStatus: "At Risk" },
      { rank: 3, advisorId: "ADV0040", advisorName: "Jamie Singh", market: "Boston", revenue: 1280000, growth: -6.9, agpStatus: "On Track" }
    ],
    insights: [
      {
        id: "ins-1",
        title: "Revenue decline risk in brokerage-heavy households",
        severity: "High",
        confidence: 0.89,
        summary: "Revenue is improving overall, but product mix shows brokerage compression and lower recurring managed revenue penetration versus peers.",
        evidence: ["Brokerage growth is -3.1%", "Managed revenue share is 38%", "Peer benchmark is 44% managed revenue share"],
        reasoningSteps: ["Compared product revenue by category", "Benchmarked managed revenue mix", "Detected gap versus peer average"],
        recommendedActions: ["Prioritize managed account review for suitable households", "Use playbook PB001", "Schedule follow-up within 10 business days"]
      },
      {
        id: "ins-2",
        title: "NNM pressure needs client engagement action",
        severity: "Medium",
        confidence: 0.82,
        summary: "NNM decreased versus prior period, driven by outflows from two large households with limited recent CRM activity.",
        evidence: ["NNM change is -2.1%", "Two households contributed 61% of outflow", "CRM activity count below market average"],
        reasoningSteps: ["Joined NNM with household activity", "Reviewed CRM meeting cadence", "Ranked households by outflow concentration"],
        recommendedActions: ["Create outreach sequence", "Review liquidity needs", "Capture meeting notes in CRM"]
      },
      {
        id: "ins-3",
        title: "AGP coaching action recommended",
        severity: "Medium",
        confidence: 0.86,
        summary: "Advisor is near AGP goal attainment but off target on meeting frequency and prospect conversion.",
        evidence: ["AGP goal attainment is 83%", "Meeting cadence is 14% below goal", "Conversion rate is 8% below target"],
        reasoningSteps: ["Checked AGP KPI status", "Detected off-track indicators", "Mapped KPI gaps to coaching playbook"],
        recommendedActions: ["MDW review", "Weekly meeting plan", "Convert scenario to coaching recommendation"]
      }
    ]
  };
}
