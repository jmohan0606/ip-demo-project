# TigerGraph Codespace Preflight — 2026-07-10

**VERDICT: NO — Codespace will serve from the mock tier.**

A real, reachable, schema-loaded TigerGraph exists in this Codespace and got very close — but
**installed-query execution cannot complete because the GSE service (graph storage/ID engine)
crashes on every startup with a corrupted ID store**, so tier 2 cannot actually serve the app's
catalogued queries. Everything up to that point works and is documented below so nothing has to
be re-litigated.

No application code was changed. No `.store` reader, service, or router was touched. The
client/cdao/remote-TigerGraph config was not modified. The only files touched: this report and
`.env` (Codespace-local graph settings, tried during the preflight, now restored to
`GRAPH_CLIENT_MODE=real` as found, with the local settings left commented for a future retry).

---

## What was found (step 1 inventory, verbatim state)

- `docker ps -a`: container `tigergraph` (image `tigergraph/community:latest`, id `310eb6dc3a78`,
  created 7 days ago) **Exited (143) 4 days ago** — killed by SIGTERM, almost certainly the
  Codespace shutdown. Ports mapped: 9000→9000, 14240→14240, 22→14022. Data volume:
  `/home/codespace/tigergraph-data → /home/tigergraph/mydata`.
- Nothing listening on 9000/14240 before start; both `curl` probes empty.
- Host resources: 2 cores, 7.8 GiB RAM, disk 89% full (3.5 GB free at start).
- TigerGraph version inside container: **4.2.3**.

## What worked (all verified with real output)

1. **Container restart**: `docker start tigergraph` → all services except GSE reach Online in
   ~3-4 min. `curl http://localhost:14240/api/ping` → `{"error":false,"message":"pong"}`;
   `curl http://localhost:9000/echo` → `{"error":false, "message":"Hello GSQL"}`.
2. **Schema already installed** from a past session: all `phx_dm_*` global vertex/edge types
   present (the older 56-vertex snapshot — see caveat below).
3. **Graph created during this preflight**: `iperform_insights_coaching_demo` created from the
   container's own copy of `foundation/schema/03_create_graph.gsql` (the graph did NOT exist
   before — global types only, `Graphs:` was empty).
4. **Data is substantially loaded** (mostly from a past session, hierarchy re-upserted now):
   `getVertexCount("*")` ≈ **23,800 vertices**, including 10,080 revenue transactions,
   360 households, 720 accounts, 60 advisors, 1,440 each monthly AUM/NCF/NNM, 4,320 monthly
   product revenue, 212 feature snapshots/embeddings/similarity matches, etc. This preflight
   loaded the full hierarchy (1 firm / 3 divisions / 6 regions / 12 markets / 24 branches /
   60 advisors) plus the 5 containment edge types via pyTigerGraph upserts, all `N/N` accepted.
   (Edge coverage beyond the hierarchy was not audited.)
5. **Tier-2 health is genuinely healthy** — the app's own client, unmodified:
   `PyTigerGraphClient().health()` → `{"healthy": true, "mode": "pytigergraph",
   "graph": "iperform_insights_coaching_demo", "echo": "Hello GSQL", "host": "http://localhost"}`.
6. **Query installation (C++ compile) WORKS on this 2-core box** — contrary to the Phase-2-era
   assumption. Two queries compiled and installed successfully, ~1:54 each:
   a corrected `get_org_hierarchy` and a minimal `t_preflight`. The one install failure seen
   ("Failed query during linking libudf") was transient — it ran while `gadmin start GSE` was
   restarting shared services; the retry succeeded.

## The blocker (why the verdict is NO)

**GSE crashes on startup, every time, including after `gadmin restart all -y`:**

```
E0710 06:28:31.054497 25500 segment_id_manager.hpp:406] invalid segment id = 1279, group_id = 14, total_group_num = 32
E0710 06:28:31.054842 25500 segment_id_manager.hpp:406] invalid segment id = 1279, group_id = 15, total_group_num = 32
(repeats across groups) ... Processor[N] loss leader ... → GSE shuts itself down
```

`gadmin status` after every start attempt: `GSE  Down  Stopped` while GPE/GSQL/RESTPP are Online.
The ID store appears corrupted — most plausibly from the SIGTERM container kill 4 days ago.

Consequence: **installed queries never complete.** Every execution attempt times out, e.g.:

```
{"error":true,"message":"The query didn't finish because it exceeded the query timeout threshold
(180 seconds). Please check GSE log for license expiration and RESTPP/GPE log with request id
(33554434.RESTPP_1_1.1783664051697.N) for details. ...","code":"REST-3000"}
```

— even for `t_preflight`, a single 1-hop traversal over 1 firm → 3 divisions. So the app's
`run_query(...)` at tier 2 (`runInstalledQuery`) cannot return results, and per-request fallback
lands on the mock tier. Upserts and vertex counts (RESTPP paths not requiring GSE ID resolution
the same way) work fine, which is why loading succeeded while queries hang.

**Bounded attempts made before stopping** (per the time-box): started GSE alone, restarted
GPE+RESTPP, full `gadmin restart all -y` — GSE dies with identical segment-id errors each time.
A repair likely means wiping GSE/GPE data stores (or the container) and re-loading from scratch
— out of scope for this preflight.

## Additional real findings worth keeping (found incidentally, verified)

1. **The foundation GSQL query files contain GSQL syntax errors and cannot install as written.**
   These were never caught because installs never ran live (Phase-2 hardware wall). Confirmed on
   TigerGraph 4.2.3 with `GQ-001_get_org_hierarchy.gsql`:
   - **Name-first parameters** — `CREATE QUERY get_org_hierarchy(scope_type STRING, ...)` is
     rejected; GSQL requires type-first: `(STRING scope_type, ...)`. The older files (GQ-001,
     GQ-002, GQ-009 checked) use the invalid form; newer ones (GQ-044) are correct. Mixed bag —
     every file needs checking.
   - **Undirected edge patterns under SYNTAX V1** — `-(edge)-` is V2 syntax; V1 needs `-(edge)->`.
   - **Vertex-set variables as traversal targets** — `-(edge)-> all_divisions:d` fails in both
     V1 and V2 on 4.2.3; rewriting to the vertex type (`-(edge)-> phx_dm_division:d`) parses and
     compiles.
   With those three fixes applied (to a temp copy only — repo files untouched), `get_org_hierarchy`
   **compiled and installed successfully**. A syntax-fix pass over all 50 query files is required
   before any live TigerGraph (including the client's) can install them.
2. **The container's schema is the older 56-vertex snapshot** — it predates the Section 13/15
   additions (`phx_dm_impact_ledger`, `phx_dm_learning_weight`, `phx_dm_rec_status_transition`,
   `phx_dm_coaching_task`, `phx_dm_reasoning_for_advisor`, etc.). A future local rebuild should
   drop and reinstall from `docs/tigergraph_foundation/` (60v/132e), per `TIGERGRAPH_AUDIT.md`.
3. **Advisor CSV loads need typed casts** via pyTigerGraph dict upserts (`tenure_months` → INT,
   `agp_flag` → BOOL); raw CSV strings are rejected with REST-30200.

## What it would take to flip this to YES (for the human to decide, not done here)

1. Wipe and recreate the container (image is already pulled, 7.4 GB on disk), or clear the
   GSE/GPE data dirs — the corrupted ID store won't heal via restarts.
2. Reinstall schema from `docs/tigergraph_foundation/` (current 60v/132e), recreate the graph.
3. Run a syntax-fix pass over the 50 GQ-*.gsql files (three defect classes above), then install
   — ~2 min compile each on this box, so ~100 min for all 50; feasible but long.
4. Reload the 192 manifest CSVs (RESTPP upsert path is proven to work).
5. Watch disk: root FS was at 82-89% during this preflight.

## Evidence trail

- Tier-2 health JSON: above, from the app's unmodified `PyTigerGraphClient`.
- Install success: `Query installation summary for graph 'iperform_insights_coaching_demo':
  succeeded: 1, skipped: 0, failed: 0.` (twice: `t_preflight`, `get_org_hierarchy`).
- Timeout + GSE crash logs: quoted verbatim above.
- Scratch artifacts (session-local, not committed): corrected query copies and loader script in
  the session scratchpad; nothing added to the repo besides this file.
