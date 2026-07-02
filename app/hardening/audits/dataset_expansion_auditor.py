from __future__ import annotations

import csv
from pathlib import Path


class DatasetExpansionAuditor:
    def __init__(self, root: str = ".") -> None:
        self.root = Path(root)

    def _count(self, rel: str) -> int:
        path = self.root / rel
        if not path.exists():
            return 0
        with path.open(encoding="utf-8") as f:
            return max(0, sum(1 for _ in csv.DictReader(f)))

    def audit(self) -> dict:
        counts = {
            "advisors": self._count("tigergraph/sample_data/phx_dm_advisor.csv"),
            "households": self._count("tigergraph/sample_data/phx_dm_household.csv"),
            "accounts": self._count("tigergraph/sample_data/phx_dm_account.csv"),
            "transactions": self._count("tigergraph/sample_data/phx_dm_transaction.csv"),
            "crm_activities": self._count("tigergraph/sample_data/phx_dm_crm_activity.csv"),
            "goals": self._count("tigergraph/sample_data/phx_dm_goal.csv"),
            "kpis": self._count("tigergraph/sample_data/phx_dm_kpi.csv"),
        }
        thresholds = {
            "advisors": 30,
            "households": 30,
            "accounts": 30,
            "transactions": 300,
            "crm_activities": 60,
            "goals": 10,
            "kpis": 10,
        }
        failures = [k for k, v in thresholds.items() if counts.get(k, 0) < v]
        return {
            "status": "passed" if not failures else "failed",
            "counts": counts,
            "thresholds": thresholds,
            "failures": failures,
        }
