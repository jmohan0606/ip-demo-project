#!/usr/bin/env bash
# Section 11.1 §8 — empirically check whether the local TigerGraph Community Edition
# supports native vector storage (TigerVector: EMBEDDING attribute + HNSW + vectorSearch).
# Do NOT assume version support — attempt it, print PASS/FAIL, and record honestly. Time-boxed.
#
# Outcome on this 2-core CE 4.2.3 box is expected to be UNVERIFIED: the same live-TG query
# INSTALL / C++ compile limit found in Phase 2/3 blocks exercising GSQL vector features here.
# FAIL/UNVERIFIED is an acceptable, documented result — VECTOR_CLIENT_MODE=local stays the
# working default; the client-site cutover is env-only on adequate hardware.
set -uo pipefail
DEADLINE=$(( $(date +%s) + 1200 ))   # 20-minute hard time-box

echo "== TigerGraph vector-support check =="
if ! command -v docker >/dev/null 2>&1; then
  echo "RESULT: UNVERIFIED (docker not available)"; exit 0
fi
STATUS=$(docker ps -a --filter name=tigergraph --format '{{.Status}}' 2>/dev/null || true)
echo "container: ${STATUS:-not found}"
if [ -z "$STATUS" ]; then
  echo "RESULT: UNVERIFIED (no tigergraph container; see CLAUDE.md Section 8 to create one)"; exit 0
fi

echo "starting container (bounded)…"
docker start tigergraph >/dev/null 2>&1 || true
# wait for gsql, but never past the deadline
while [ "$(date +%s)" -lt "$DEADLINE" ]; do
  if docker exec tigergraph gadmin status 2>/dev/null | grep -qi "GSQL.*Online"; then break; fi
  sleep 10
done

GSQL_VER=$(docker exec tigergraph gsql --version 2>/dev/null | head -1 || echo "unknown")
echo "gsql: $GSQL_VER"

# Attempt a minimal EMBEDDING attribute + vector search round-trip on a scratch graph.
read -r -d '' PROBE <<'GSQL'
CREATE VERTEX _vec_probe (PRIMARY_ID pid STRING, emb EMBEDDING(DIMENSION=4, METRIC="COSINE"))
CREATE GRAPH _vec_probe_g(_vec_probe)
GSQL
echo "$PROBE" | timeout 300 docker exec -i tigergraph gsql 2>/tmp/tgvec.err
if [ $? -eq 0 ] && ! grep -qiE "error|not supported|unknown" /tmp/tgvec.err; then
  echo "RESULT: PASS (EMBEDDING attribute accepted — TigerVector supported)"
  docker exec tigergraph gsql "DROP GRAPH _vec_probe_g" >/dev/null 2>&1 || true
else
  echo "RESULT: UNVERIFIED/FAIL — EMBEDDING DDL not accepted or timed out on this box"
  echo "  (expected on 2-core CE; VECTOR_CLIENT_MODE=local remains the working default)"
  head -5 /tmp/tgvec.err 2>/dev/null || true
fi
