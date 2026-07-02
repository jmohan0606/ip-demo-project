# TigerGraph Source of Truth

## Use this folder only

```text
tigergraph/
  schema/phx_dm_iperform_enterprise_schema.gsql
  queries_v1/phx_dm_*.gsql
  loading/phx_dm_production_loading_job.gsql
  sample_data/phx_dm_*.csv
```

## Do not use

```text
gsql/
```

The conflicting root `gsql/` folder has been removed from this corrected package.

## Graph name

```text
iperform_insights_coaching_demo
```

## Prefixes

```text
Vertex prefix: phx_dm_
Edge prefix:   phx_dm_
Query prefix:  phx_dm_
CSV prefix:    phx_dm_
```

## Installed analytics queries

```text
phx_dm_get_advisor_context
phx_dm_get_revenue_summary
phx_dm_get_advisor_360
phx_dm_get_recommendation_context
phx_dm_get_memory_timeline
phx_dm_get_graph_explorer
```

## MCP execution

MCP tool name is **not** the analytics query name.

The application calls:

```text
tigergraph__run_installed_query
```

with:

```json
{
  "graph_name": "iperform_insights_coaching_demo",
  "query_name": "phx_dm_get_advisor_context",
  "params": {"advisor_id": "ADV0001"}
}
```

## RESTPP fallback

RESTPP executes the same installed queries using:

```text
GET /query/iperform_insights_coaching_demo/phx_dm_get_advisor_context?advisor_id=ADV0001
```

## Install

```bash
bash scripts/install_tigergraph_source_of_truth.sh
```

## Validate package consistency

```bash
uv run python scripts/validate_tigergraph_source_of_truth.py
```
