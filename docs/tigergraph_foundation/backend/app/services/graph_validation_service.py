from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from .. import db
from ..config import settings
from .manifest_service import ManifestService
from .tigergraph_client import TigerGraphClient

class GraphValidationService:
    def __init__(self):
        self.manifest = ManifestService()
        self.tg = TigerGraphClient()

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    def cardinality(self, run_id: str | None = None) -> dict:
        manifest = self.manifest.entries()
        expected = {"vertex": {}, "edge": {}}
        for entry in manifest:
            expected[entry["kind"]][entry["target"]] = expected[entry["kind"]].get(entry["target"], 0) + self.manifest.inspect(entry)["actual_rows"]
        if settings.mock_tigergraph:
            actual = expected
            mode = "mock"
        else:
            actual = {"vertex": {}, "edge": {}}
            for kind in ("vertex", "edge"):
                response = self.tg.statistics(kind)
                key_type = "v_type" if kind == "vertex" else "e_type"
                for item in response.get("results", []):
                    actual[kind][item[key_type]] = int(item.get("count", 0))
            mode = "live"
        results = []
        for kind in ("vertex", "edge"):
            for target, exp in sorted(expected[kind].items()):
                act = actual[kind].get(target, 0)
                status = "PASS" if act == exp else "FAIL"
                row = {"rule_id": f"COUNT_{kind.upper()}_{target}", "domain": "CARDINALITY", "severity": "ERROR", "status": status, "expected": exp, "actual": act, "message": f"{kind} count for {target}"}
                results.append(row)
                db.execute(
                    "INSERT INTO graph_validation_result(run_id,rule_id,domain,severity,status,expected_value,actual_value,message,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                    (run_id, row["rule_id"], row["domain"], row["severity"], status, str(exp), str(act), row["message"], self._now()),
                )
        return {"mode": mode, "passed": all(x["status"] == "PASS" for x in results), "results": results}

    def query_smoke(self) -> dict:
        cases_path = Path(settings.query_cases_path)
        cases = json.loads(cases_path.read_text(encoding="utf-8"))["cases"]
        results = []
        for case in cases:
            try:
                response = self.tg.run_query(case["query_name"], case.get("params", {}))
                results.append({"id": case["id"], "query_name": case["query_name"], "status": "PASS", "mock": bool(response.get("mock"))})
            except Exception as exc:
                results.append({"id": case["id"], "query_name": case["query_name"], "status": "FAIL", "error": str(exc)})
        return {"passed": all(x["status"] == "PASS" for x in results), "results": results, "mode": "mock" if settings.mock_tigergraph else "live"}
