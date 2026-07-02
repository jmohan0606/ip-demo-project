#!/usr/bin/env bash
set -euo pipefail

echo "Installing TigerGraph source of truth: tigergraph/"
echo "Graph: ${TG_GRAPHNAME:-iperform_insights_coaching_demo}"

gsql tigergraph/schema/phx_dm_iperform_enterprise_schema.gsql

for q in tigergraph/queries_v1/*.gsql; do
  echo "Installing query: $q"
  gsql "$q"
done

echo "Installing loading job..."
gsql tigergraph/loading/phx_dm_production_loading_job.gsql

echo "TigerGraph source-of-truth install complete."
