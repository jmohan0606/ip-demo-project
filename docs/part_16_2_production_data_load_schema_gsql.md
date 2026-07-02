# Part 16.2 — Production Data Load, Schema Verification & GSQL Query Installation

## Added

- Enterprise TigerGraph schema
- Production query contracts
- GSQL analytical queries
- GSQL loading job
- Schema contract verification script
- Linux/macOS installation script
- Windows PowerShell installation script
- Validation report generation

## Schema coverage

Includes vertices for:

- Hierarchy: Firm, Division, Region, Market, Advisor
- Client book: Household, Account, Product, RevenueTransaction
- AI system: Opportunity, Recommendation, Feedback, Memory, ContextPacket
- Operations: AgentExecution, ToolCall
- Knowledge: Document, DocumentChunk
- AI/ML: FeatureVector, Prediction, Scenario
- Compliance: ComplianceRule, ComplianceCheck

## Query coverage

```text
get_advisor_context
get_revenue_summary
get_advisor_360
get_recommendation_context
get_memory_timeline
get_graph_explorer
```

## Install

Linux/macOS:

```bash
bash scripts/install_tigergraph_gsql_queries.sh
```

Windows:

```powershell
./scripts/install_tigergraph_gsql_queries.ps1
```

## Validate locally

```bash
uv run python scripts/validate_part_16_2.py
uv run python scripts/verify_tigergraph_schema_contracts.py
```

## Next step

Part 16.3 — Real Azure OpenAI / LLM Agent Activation.
