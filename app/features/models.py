from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FeatureVector:
    entity_type: str
    entity_id: str
    features: dict[str, float]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PredictionResult:
    target: str
    baseline: float
    predicted: float
    confidence: float
    drivers: list[dict[str, Any]]
    scenario_delta: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SimilarityResult:
    entity_id: str
    entity_name: str
    similarity: float
    explanation: str
    features_matched: list[str] = field(default_factory=list)
