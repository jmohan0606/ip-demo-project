# Part 17.5 — Enterprise UI + TigerGraph Consolidated Package

This package merges:
- Part 17 Emergency UI Remediation
- Corrected TigerGraph Source of Truth
- Corrected MCP/RESTPP configuration
- RESTPP sample data loader to bypass broken loading jobs

Use this package only.

Validate:
```bash
uv run python scripts/validate_part17_5_consolidated.py
uv run python scripts/validate_tigergraph_source_of_truth.py
```

Install TigerGraph schema/queries:
```bash
bash scripts/install_tigergraph_source_of_truth.sh
```

Load sample data without loading jobs:
```bash
export TIGERGRAPH_RESTPP_URL=http://<host>:9000
export TG_GRAPHNAME=iperform_insights_coaching_demo
export TG_API_TOKEN=<token>
uv run python scripts/load_tigergraph_sample_data_restpp.py
```

Run app:
```bash
uv run python run_local_api.py
cd frontend
npm install lucide-react recharts
npm run dev
```
