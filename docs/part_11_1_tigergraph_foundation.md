# Part 11.1 — TigerGraph Foundation Package

## Included

- New graph name: `iperform_insights_coaching_demo`
- Prefix convention: `phx_dm_`
- TigerGraph 4.2.2 / V1-first design
- Schema files:
  - `tigergraph/schema/01_vertices.gsql`
  - `tigergraph/schema/02_edges.gsql`
  - `tigergraph/schema/03_create_graph.gsql`
- V1 query files in `tigergraph/queries_v1`
- V2 backup folder reserved for later
- Schema inventory service
- API endpoints:
  - `/tigergraph-foundation/inventory`
  - `/tigergraph-foundation/files`
  - `/tigergraph-foundation/validate-prefix`

## WebShell Execution Order

```text
1. tigergraph/schema/01_vertices.gsql
2. tigergraph/schema/02_edges.gsql
3. tigergraph/schema/03_create_graph.gsql
4. tigergraph/queries_v1/*.gsql
5. tigergraph/queries_v1/00_install_all_v1_queries.gsql
```

## Notes

This package does not yet generate enterprise demo data. That starts in Part 11.2.
