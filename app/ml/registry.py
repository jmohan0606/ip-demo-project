from __future__ import annotations

"""Model registry (Section 11.1 §10).

A committed JSON file (`models/registry.json`) holds metrics + metadata only — no
binary weights. Trained artifacts live under `models/artifacts/` (gitignored). The
registry is the single source of truth for (a) which real model, if any, is eligible
to serve a prediction type (the precedence/quality gate in §2), and (b) the model-card
content rendered on the Admin page.

This module has NO heavy-ML imports — it is safe to import from business code.
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from app.config.settings import get_settings

REGISTRY_PATH = Path("models/registry.json")


def artifact_dir() -> Path:
    """Directory holding trained binary artifacts (gitignored). Created on demand."""
    settings = get_settings()
    d = Path(getattr(settings, "ml_artifacts_dir", "models/artifacts"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_registry() -> dict[str, Any]:
    """Full registry document: {"models": {name: entry, ...}, "schema_version": 1}."""
    if not REGISTRY_PATH.exists():
        return {"schema_version": 1, "models": {}}
    try:
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"schema_version": 1, "models": {}}


def list_entries() -> list[dict[str, Any]]:
    return list(load_registry().get("models", {}).values())


def get_entry(name: str) -> dict[str, Any] | None:
    return load_registry().get("models", {}).get(name)


def upsert_entry(entry: dict[str, Any]) -> None:
    """Atomically insert/replace a registry entry keyed by entry['name'].

    Training scripts call this after printing their real metrics block. The write is
    atomic (temp file + os.replace) so a crash mid-write can't corrupt the committed
    registry.
    """
    if "name" not in entry:
        raise ValueError("registry entry requires a 'name'")
    doc = load_registry()
    doc.setdefault("models", {})[entry["name"]] = entry
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(REGISTRY_PATH.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, sort_keys=True)
        os.replace(tmp, REGISTRY_PATH)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def serves(name: str) -> bool:
    """True iff this model's registry entry passes its quality gate and has an artifact.

    This is the precedence gate from §2: a real model only serves the live path when it
    is present AND passed its metric floor / leakage checks at training time.
    """
    entry = get_entry(name)
    if not entry:
        return False
    if entry.get("quality_gate") != "passed":
        return False
    artifact = entry.get("artifact_path")
    return bool(artifact) and Path(artifact).exists()
