from __future__ import annotations

"""Section 11.5 — read-only Evaluation & Trust endpoints.

Serves the COMMITTED golden-eval run files (never live state) so the Admin tab can render the
latest real Claude run + the trend. No POST/run — the harness is a CLI by design (it needs
LLM_CLIENT_MODE=claude and a real key; a button that silently ran mock would defeat the point).
"""

import json
from pathlib import Path

from fastapi import APIRouter

from app.shared.responses import ok

router = APIRouter(prefix="/evaluation", tags=["Evaluation & Trust"])

# Resolve relative to the repo root (this file is app/api/routers/evaluation.py) so it works
# regardless of the server's CWD.
_EVAL_DIR = Path(__file__).resolve().parents[3] / "docs/section11/eval"
_HISTORY = _EVAL_DIR / "run_history.json"
_RUNS = _EVAL_DIR / "runs"


@router.get("/runs")
def runs():
    """Trend history — one summary row per committed eval run."""
    history = json.loads(_HISTORY.read_text()) if _HISTORY.exists() else []
    return ok(data={"history": history, "count": len(history)})


@router.get("/runs/latest")
def latest_run():
    """The newest committed run's full per-question detail."""
    if not _RUNS.exists():
        return ok(data={"available": False, "hint": "Run: LLM_CLIENT_MODE=claude python scripts/eval/run_golden_eval.py"})
    files = sorted(_RUNS.glob("run_*.json"))
    if not files:
        return ok(data={"available": False, "hint": "No eval runs yet — run scripts/eval/run_golden_eval.py"})
    run = json.loads(files[-1].read_text())
    return ok(data={"available": True, **run})
