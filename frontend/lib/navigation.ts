import type { NavigationItem } from "@/lib/types/navigation";

export const navigationItems: NavigationItem[] = [
  {
    id: "executive-dashboard",
    label: "Executive Dashboard",
    description: "Revenue, AUM, NNM, NCF, insights, coaching and hierarchy performance.",
    href: "/dashboard",
    iconName: "LayoutDashboard",
    group: "Executive",
    status: "ready"
  },
  {
    id: "revenue-analytics",
    label: "Revenue Analytics",
    description: "Revenue trends, product mix, drilldowns and transaction lineage.",
    href: "/revenue-analytics",
    iconName: "LineChart",
    group: "Executive"
  },
  {
    id: "advisor-360",
    label: "Advisor 360 / Client 360",
    description: "Advisor, household, account, transaction, CRM, AUM, NNM and NCF detail.",
    href: "/advisor-360",
    iconName: "Users",
    group: "Advisor"
  },
  {
    id: "agp-workspace",
    label: "AGP Goals & Coaching",
    description: "Advisor Growth Program goals, KPIs, on/off-track coaching and MDW/DDW review.",
    href: "/agp",
    iconName: "Target",
    group: "Advisor"
  },
  {
    id: "client-360",
    label: "Client Intelligence 360",
    description: "Household profile: accounts, product holdings, transactions and AI recommendations.",
    href: "/client-360",
    iconName: "UserCircle",
    group: "Advisor"
  },
  {
    id: "coaching-reviews",
    label: "Coaching & Reviews",
    description: "Coaching sessions, action items and manager reviews per advisor.",
    href: "/coaching-reviews",
    iconName: "BookOpenCheck",
    group: "Advisor"
  },
  {
    id: "crm-activities",
    label: "CRM Activities",
    description: "Leads, referrals, opportunities, pipeline stages and overdue work per advisor.",
    href: "/crm-activities",
    iconName: "Contact",
    group: "Advisor"
  },
  {
    id: "peer-benchmarking",
    label: "Peer Benchmarking",
    description: "Percentile radar vs the scope's peer group + nearest peers from the similarity model.",
    href: "/peer-benchmarking",
    iconName: "Radar",
    group: "Advisor"
  },
  {
    id: "what-if-simulator",
    label: "What-If Simulator",
    description: "Scenario modeling for meetings, conversion, product mix, managed revenue, NNM and AUM.",
    href: "/what-if",
    iconName: "SlidersHorizontal",
    group: "AI",
    status: "new"
  },
  {
    id: "prediction-forecasting",
    label: "Prediction & Forecasting",
    description: "Revenue, NNM, AUM, AGP, opportunity, churn and growth predictions.",
    href: "/predictions",
    iconName: "Activity",
    group: "AI",
    status: "new"
  },
  {
    id: "opportunities-recommendations",
    label: "Opportunities & Recommendations",
    description: "Opportunity ranking, recommendation queue, evidence, compliance and action workflow.",
    href: "/recommendations",
    iconName: "Sparkles",
    group: "AI"
  },
  {
    id: "recommendation-roi",
    label: "Recommendation Impact / ROI",
    description: "Accepted/rejected recommendations, business impact, outcomes and learning signals.",
    href: "/recommendation-roi",
    iconName: "TrendingUp",
    group: "AI"
  },
  {
    id: "ai-assistant",
    label: "AI Assistant",
    description: "Separate context-aware advisor chat with evidence, tool calls and agent steps.",
    href: "/ai-assistant",
    iconName: "Bot",
    group: "AI"
  },
  {
    id: "knowledge-playbooks",
    label: "Knowledge / Playbooks / Compliance",
    description: "Practice guidelines, compliance docs, playbooks, RAG search and guardrails.",
    href: "/knowledge",
    iconName: "BookOpenCheck",
    group: "AI"
  },
  {
    id: "graph-explorer",
    label: "Knowledge Graph Explorer",
    description: "Advisor, household, account, product, memory, recommendation and opportunity graph.",
    href: "/graph-explorer",
    iconName: "Network",
    group: "Graph"
  },
  {
    id: "features-embeddings",
    label: "Feature Store / Embeddings / Similarity",
    description: "Feature vectors, graph embeddings, peer similarity and household similarity.",
    href: "/features-embeddings",
    iconName: "GitBranch",
    group: "Graph"
  },
  {
    id: "memory-explainability",
    label: "Memory Timeline & Explainability",
    description: "Temporal memory, reasoning traces, evidence chains and why/how explanation.",
    href: "/memory-explainability",
    iconName: "BrainCircuit",
    group: "Graph"
  },
  {
    id: "agent-observability",
    label: "Agent Orchestration & Observability",
    description: "Supervisor flow, LangGraph trace, tool calls, latency and errors.",
    href: "/agents",
    iconName: "Workflow",
    group: "Operations"
  },
  {
    id: "data-ingestion",
    label: "Data Ingestion & Sync",
    description: "CSV upload, validation, progress, retry/resume and MCP-first load status.",
    href: "/data-ingestion",
    iconName: "UploadCloud",
    group: "Operations"
  },
  {
    id: "admin-health",
    label: "Admin / Data Quality / Runtime Health",
    description: "Data freshness, missing data, MCP/REST/mock, Chroma, SQLite and hardening status.",
    href: "/admin",
    iconName: "ShieldCheck",
    group: "Admin",
    status: "audit"
  }
];

export const navigationGroups = ["Executive", "Advisor", "AI", "Graph", "Operations", "Admin"] as const;
