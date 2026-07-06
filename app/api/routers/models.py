from fastapi import APIRouter

from app.ml import registry
from app.shared.responses import ok

router = APIRouter(prefix="/admin/models", tags=["Model Registry"])


@router.get("")
def list_models():
    """Model registry (Section 11.1 §10) — every trained model's metrics + metadata."""
    entries = registry.list_entries()
    return ok(data={
        "count": len(entries),
        "serving": [e["name"] for e in entries if e.get("quality_gate") == "passed"],
        "models": sorted(entries, key=lambda e: e.get("name", "")),
    })


@router.get("/{name}")
def model_card(name: str):
    """Full model card for one model (algorithm, training data, metrics, caveats)."""
    entry = registry.get_entry(name)
    return ok(data=entry or {"error": f"no model '{name}' in registry"})
