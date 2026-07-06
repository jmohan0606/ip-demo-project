"""Section 11.5 — Evaluation & Trust harness.

Runs the golden Q&A set through the REAL Coach Q&A path (RagGenerationService.answer, the
identical path behind POST /knowledge/ask) and scores groundedness, citation coverage and
refusal correctness. Deterministic keyword scoring — no LLM judge.

Usage:
  LLM_CLIENT_MODE=claude python scripts/eval/run_golden_eval.py       # real run (needs key)
  python scripts/eval/run_golden_eval.py --retrieval-check           # retrieval only, no LLM

Fails loudly unless LLM_CLIENT_MODE=claude for a scoring run — mock output is templated and
cannot demonstrate groundedness. A low score is a truthful result (exit 0); only infrastructure
failures exit non-zero.
"""
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "docs/section11/eval/golden_qa.json"
RUNS_DIR = ROOT / "docs/section11/eval/runs"
HISTORY = ROOT / "docs/section11/eval/run_history.json"

CITE_RE = re.compile(r"\[(\d+)\]")
# Honest non-coverage signal — the generation-side refusal (the corpus is broad finance
# language, so near-domain questions retrieve chunks; the hallucination guard is that Claude
# then SAYS the passages don't cover it rather than fabricating).
DECLINE_RE = re.compile(
    r"(do(es)?\s+not\s+(contain|address|cover|include|mention|provide|specify|discuss)"
    r"|not\s+contain(ed)?|no\s+information|does\s+not\s+appear|cannot\s+(answer|find|provide|determine)"
    r"|would\s+need\s+(access|additional)|not\s+(in|within|covered)\s+(the\s+)?(provided|source|available)"
    r"|not\s+covered|isn'?t\s+(in|covered|addressed)|do\s+not\s+have|no\s+(passage|source|document))",
    re.IGNORECASE)


def _present(point: dict, text: str) -> bool:
    t = text.lower()
    return all(any(term.lower() in t for term in group) for group in point["groups"])


def _load_golden() -> dict:
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


def _ingest_corpus():
    from app.services.knowledge_management_service import KnowledgeManagementService

    svc = KnowledgeManagementService()
    results = svc.ingest_sample_knowledge()
    return len({getattr(r, "document_id", getattr(r, "document_name", i)) for i, r in enumerate(results)}), svc


def retrieval_check(golden: dict) -> int:
    """Unit-1 gate: every grounded item retrieves a must_cite doc above 0.30; every refusal
    retrieves nothing. Needs no LLM/key. Returns process exit code."""
    from app.knowledge.rag_service import RagGenerationService

    _ingest_corpus()
    rag = RagGenerationService()
    ok = True
    for item in golden["items"]:
        sources = rag.retrieve(item["question"], top_k=5)
        docs = {s["document_name"] for s in sources}
        if item["type"] == "grounded":
            hit = bool(docs & set(item["must_cite"]))
            print(f"  {item['id']} grounded: retrieved {len(sources)} · must_cite_hit={hit} · docs={sorted(docs)[:3]}")
            if not hit:
                ok = False
        else:
            # Refusals are validated by the generation-side honest-decline in the real run —
            # with a broad finance corpus + a 0.30 floor, near-domain questions DO retrieve
            # chunks, so found=false is not expected here. Informational only.
            print(f"  {item['id']} refusal: retrieved {len(sources)} chunks (validated by honest-decline in the real run)")
    print("\nRETRIEVAL GATE (grounded must_cite retrievable):", "PASS" if ok else "FAIL")
    return 0 if ok else 2


def _score_item(item: dict, result: dict) -> dict:
    answer = result.get("answer", "") or ""
    sources = result.get("sources", []) or []
    evidence = " ".join(s.get("excerpt", "") for s in sources)
    cited_docs = {s.get("document_name", "") for s in sources}
    found = result.get("found", False)

    if item["type"] == "refusal":
        # PASS = honest decline: either the retrieval-refusal path (found=false, no LLM call)
        # OR the generation-refusal path (found=true but the answer says the passages don't
        # cover it). A fabricated answer that asserts uncited policy is a FAIL.
        honest_decline = (not found) or bool(DECLINE_RE.search(answer))
        return {"id": item["id"], "type": "refusal", "found": found, "pass": honest_decline,
                "groundedness_score": None, "has_citation": None, "must_cite_hit": None,
                "declined": honest_decline, "cited_docs": sorted(cited_docs), "point_results": [],
                "answer_excerpt": (answer[:400] if found else "(honest not-found — no LLM call)"),
                "sources": [{"document_name": s.get("document_name"), "similarity": s.get("similarity")} for s in sources]}

    points = item["expected_answer_points"]
    point_results = []
    grounded = 0
    for p in points:
        in_ans = _present(p, answer)
        in_ev = _present(p, evidence)
        pg = in_ans and in_ev
        grounded += 1 if pg else 0
        point_results.append({"label": p["label"], "in_answer": in_ans, "in_evidence": in_ev})
    g_score = round(grounded / len(points), 3) if points else 0.0
    markers = [int(m) for m in CITE_RE.findall(answer)]
    has_citation = found and len(sources) >= 1 and any(1 <= n <= len(sources) for n in markers)
    must_cite_hit = bool(cited_docs & set(item["must_cite"]))
    passed = bool(found and has_citation and must_cite_hit and g_score >= 0.6)
    return {"id": item["id"], "type": "grounded", "found": found, "pass": passed,
            "groundedness_score": g_score, "has_citation": has_citation, "must_cite_hit": must_cite_hit,
            "cited_docs": sorted(cited_docs), "point_results": point_results,
            "answer_excerpt": answer[:400],
            "sources": [{"document_name": s.get("document_name"), "similarity": s.get("similarity")} for s in sources]}


def run_eval(golden: dict) -> int:
    from app.config.settings import get_settings

    if get_settings().llm_client_mode.lower() != "claude":
        print("Eval requires LLM_CLIENT_MODE=claude (real answers). Mock output is templated and "
              "cannot demonstrate groundedness. Refusing to run.", file=sys.stderr)
        return 1
    try:
        from app.llm.client import get_llm_client
        get_llm_client()  # ClaudeLLMClient raises if ANTHROPIC_API_KEY missing
    except Exception as exc:  # noqa: BLE001
        print(f"Cannot initialise Claude client: {exc}", file=sys.stderr)
        return 1

    doc_count, _ = _ingest_corpus()
    if doc_count != golden["corpus_expected_docs"]:
        print(f"Corpus drift: expected {golden['corpus_expected_docs']} docs, ingested {doc_count}. "
              "Golden set may be stale — aborting.", file=sys.stderr)
        return 1

    from app.knowledge.rag_service import RagGenerationService
    rag = RagGenerationService()

    questions, first_gen = [], None
    for item in golden["items"]:
        result = rag.answer(question=item["question"], top_k=5)
        gen = result.get("generated_by", {})
        if item["type"] == "grounded" and result.get("found"):
            if gen.get("mode") != "claude":
                print(f"ABORT: {item['id']} answered by mode={gen.get('mode')} not claude.", file=sys.stderr)
                return 1
            first_gen = first_gen or gen
        questions.append(_score_item(item, result))

    grounded = [q for q in questions if q["type"] == "grounded"]
    refusals = [q for q in questions if q["type"] == "refusal"]
    g_scored = [q["groundedness_score"] for q in grounded]
    aggregates = {
        "groundedness_pct": round(100 * sum(g_scored) / len(g_scored), 1) if g_scored else 0.0,
        "citation_coverage_pct": round(100 * sum(1 for q in grounded if q["has_citation"]) / len(grounded), 1) if grounded else 0.0,
        "refusal_correctness_pct": round(100 * (sum(1 for q in refusals if q["pass"]) + sum(1 for q in grounded if q["found"])) / len(questions), 1),
        "pass_rate_pct": round(100 * sum(1 for q in questions if q["pass"]) / len(questions), 1),
        "pass_count": sum(1 for q in questions if q["pass"]), "total": len(questions),
    }
    now = dt.datetime.now(dt.timezone.utc)
    run_id = "run_" + now.strftime("%Y%m%dT%H%M%SZ")
    run = {"run_id": run_id, "timestamp_utc": now.isoformat(), "golden_version": golden["version"],
           "llm": first_gen or {"mode": "claude"}, "corpus_doc_count": doc_count,
           "aggregates": aggregates, "questions": questions}
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    (RUNS_DIR / f"{run_id}.json").write_text(json.dumps(run, indent=2))
    history = json.loads(HISTORY.read_text()) if HISTORY.exists() else []
    history.append({"run_id": run_id, "timestamp_utc": now.isoformat(), "golden_version": golden["version"],
                    "model": (first_gen or {}).get("model"), **aggregates})
    HISTORY.write_text(json.dumps(history, indent=2))

    print("=" * 72)
    print(f"GOLDEN EVAL — {run_id}")
    print("=" * 72)
    for q in questions:
        mark = "PASS" if q["pass"] else "FAIL"
        extra = f"g={q['groundedness_score']} cite={q['has_citation']} must={q['must_cite_hit']}" if q["type"] == "grounded" else f"found={q['found']}"
        print(f"  [{mark}] {q['id']} ({q['type']}) {extra}")
    print("\nAGGREGATES:", json.dumps(aggregates, indent=2))
    print(f"\nSaved → {RUNS_DIR / (run_id + '.json')} + run_history.json")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--retrieval-check", action="store_true")
    args = ap.parse_args()
    g = _load_golden()
    sys.exit(retrieval_check(g) if args.retrieval_check else run_eval(g))
