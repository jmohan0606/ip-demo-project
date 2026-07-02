#!/usr/bin/env bash
set -euo pipefail

GRAPH_NAME="${TIGERGRAPH_GRAPH:-iPerformInsights}"

echo "Installing schema..."
gsql gsql/schema/iperform_enterprise_schema.gsql

echo "Installing queries..."
for q in gsql/queries/*.gsql; do
  echo "Installing $q"
  gsql "$q"
done

echo "Installing loading job..."
gsql gsql/loading/production_loading_job.gsql

echo "TigerGraph GSQL installation complete for graph: ${GRAPH_NAME}"
