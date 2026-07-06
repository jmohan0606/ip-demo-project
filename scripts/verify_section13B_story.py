"""Section 13B.5 — story-mode / pipeline-trace verification (API-level assertions).

Cross-checks the pipeline-trace stages against their independent sources, confirms
the observability stage-spans go from empty→populated, and exercises the replayable
reset round-trip. The guided-overlay end-to-end (12 stops) is evidenced separately
via Playwright screenshots in docs/qa_screenshots/section13B/.

Usage: python3 scripts/verify_section13B_story.py   (backend must be up on :8000)
"""
from __future__ import annotations

import json
import sys
import urllib.request

B = "http://127.0.0.1:8000"
ADV = "A005"


def get(u):
    return json.load(urllib.request.urlopen(B + u))["data"]


def post(u, b=None):
    req = urllib.request.Request(B + u, data=json.dumps(b or {}).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    return json.load(urllib.request.urlopen(req))["data"]


def main() -> int:
    ok_all = True

    def check(name, cond):
        nonlocal ok_all
        print(f"   [{'PASS' if cond else 'FAIL'}] {name}")
        ok_all = ok_all and cond

    print("=== Section 13B.1/13B.2 verification (advisor A005) ===")
    post(f"/recommendations/lifecycle/reset/{ADV}")

    print("\n1. Generate + pipeline-trace cross-checks")
    gen = post(f"/recommendations/generate/{ADV}")
    rec = gen["recommendations"][0]
    rid = rec["recommendation_id"]
    tr = get(f"/explainability/pipeline-trace/{rid}")
    stages = {s["key"]: s for s in tr["stages"]}
    check("trace has all 6 stages", set(stages) == {"data", "features", "model", "derivation", "context_compliance", "output"})
    # features.revenue_ltm == snapshot revenue_ltm
    snap_rev = get(f"/features/snapshot/{ADV}")["features"]["revenue_ltm"]
    tf = {f["name"]: f["value"] for f in stages["features"]["artifact"]["top_features"]}
    check("trace feature revenue_ltm == snapshot revenue_ltm", abs((tf.get("revenue_ltm") or 0) - snap_rev) < 0.01)
    # derivation estimated impact == rec payload
    check("trace derivation impact == rec estimated impact",
          abs(stages["derivation"]["artifact"]["recommendation"]["estimated_revenue_impact"] - rec["estimated_revenue_impact"]) < 0.01)
    # compliance status == rec payload compliance
    check("trace compliance status == rec compliance status",
          stages["context_compliance"]["artifact"]["compliance"]["status"] == rec["compliance"]["status"])
    print(f"   timing_basis={tr['timing_basis']} total_ms={tr['total_ms']}")

    print("\n2. Observability stage-spans populated (was empty before 13B)")
    spans = get("/observability/stage-spans")
    span_list = spans.get("spans", spans) if isinstance(spans, dict) else spans
    check("at least one recommendation-pipeline stage span exists",
          any("recommendation-pipeline" in s.get("request", "") for s in span_list))

    print("\n3. Replayable reset round-trip (same process)")
    post("/feedback-learning/submit", {"recommendation_id": rid, "action": "complete", "action_family": rec["action_family"], "user_id": ADV})
    led_after = get(f"/impact-ledger/advisor/{ADV}")["totals"]["completed_count"]
    r = post(f"/recommendations/lifecycle/reset/{ADV}")
    led_reset = get(f"/impact-ledger/advisor/{ADV}")["totals"]["completed_count"]
    rev_reset = get(f"/revenue/analytics?scope_type=ADVISOR&scope_id={ADV}&period=LTM")["kpis"]["total_revenue"]
    check("completion recorded then reset cleared it", led_after == 1 and led_reset == 0)
    check("reset restored base revenue (same process, no restart)", abs(rev_reset - 406375.14) < 1.0)
    print(f"   reset report: {r}")

    print("\n4. Anchored guard")
    try:
        urllib.request.urlopen(urllib.request.Request(B + "/recommendations/lifecycle/reset/A001", method="POST"))
        check("A001 reset refused (403)", False)
    except urllib.error.HTTPError as e:
        check("A001 reset refused (403)", e.code == 403)

    print("\n" + ("=== ALL CHECKS PASSED ===" if ok_all else "=== SOME CHECKS FAILED ==="))
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
