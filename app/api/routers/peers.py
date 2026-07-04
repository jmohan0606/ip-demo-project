from __future__ import annotations

from fastapi import APIRouter

from app.peers.benchmarking import PeerBenchmarkingService
from app.shared.responses import ok

router = APIRouter(prefix="/peers", tags=["Peer Benchmarking"])


@router.get("/benchmark")
def benchmark(advisor_id: str = "A001", scope_type: str = "FIRM", scope_id: str = "F001"):
    """Percentile radar of an advisor vs the scope's real peer group + nearest
    peers from the similarity model."""
    return ok(data=PeerBenchmarkingService().benchmark(advisor_id=advisor_id, scope_type=scope_type, scope_id=scope_id))
