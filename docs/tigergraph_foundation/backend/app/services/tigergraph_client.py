from __future__ import annotations
import json
from typing import Any
import httpx
from ..config import settings

class TigerGraphError(RuntimeError):
    pass

class PartialUpsertError(TigerGraphError):
    def __init__(self, message: str, response: dict, accepted: int, requested: int):
        super().__init__(message)
        self.response = response
        self.accepted = accepted
        self.requested = requested

class TigerGraphClient:
    def __init__(self):
        self.base = settings.restpp_url
        self.headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if settings.tigergraph_token:
            self.headers["Authorization"] = f"Bearer {settings.tigergraph_token}"

    def _client(self) -> httpx.Client:
        return httpx.Client(verify=settings.tigergraph_verify_ssl, timeout=settings.tigergraph_timeout_seconds)

    def health(self) -> dict:
        if settings.mock_tigergraph:
            return {"healthy": True, "mode": "mock", "graph": settings.graph_name, "restpp_url": self.base}
        try:
            with self._client() as client:
                response = client.get(f"{self.base}/echo", headers=self.headers)
                response.raise_for_status()
            return {"healthy": True, "mode": "live", "graph": settings.graph_name, "restpp_url": self.base, "response": response.text}
        except Exception as exc:
            return {"healthy": False, "mode": "live", "graph": settings.graph_name, "restpp_url": self.base, "error": str(exc)}

    def _attributes(self, entry: dict, row: dict, excluded: set[str]) -> dict:
        attributes: dict[str, dict[str, Any]] = {}
        for source_column, graph_attribute in entry.get("columns", {}).items():
            if source_column in excluded:
                continue
            value = row.get(source_column)
            if value in ("", None):
                continue
            attributes[graph_attribute] = {"value": self._coerce(value)}
        return attributes

    def build_payload(self, entry: dict, records: list[dict]) -> dict:
        if entry["kind"] == "vertex":
            target = entry["target"]
            id_col = entry["id_column"]
            vertices = {target: {}}
            for row in records:
                vertex_id = str(row[id_col]).strip()
                if not vertex_id:
                    raise TigerGraphError(f"Blank vertex id in {entry['file']}")
                vertices[target][vertex_id] = self._attributes(entry, row, {id_col})
            return {"vertices": vertices}

        edge_name = entry["target"]
        edges: dict = {entry["from_type"]: {}}
        for row in records:
            from_id = str(row[entry["from_column"]]).strip()
            to_id = str(row[entry["to_column"]]).strip()
            if not from_id or not to_id:
                raise TigerGraphError(f"Blank edge endpoint in {entry['file']}")
            target_map = (
                edges.setdefault(entry["from_type"], {})
                .setdefault(from_id, {})
                .setdefault(edge_name, {})
                .setdefault(entry["to_type"], {})
            )
            target_map[to_id] = self._attributes(entry, row, {entry["from_column"], entry["to_column"]})
        return {"edges": edges}

    @staticmethod
    def _accepted_count(data: dict, kind: str) -> int:
        key = "accepted_vertices" if kind == "vertex" else "accepted_edges"
        if isinstance(data.get(key), int):
            return int(data[key])
        total = 0
        results = data.get("results", [])
        if isinstance(results, list):
            for item in results:
                if isinstance(item, dict):
                    value = item.get(key)
                    if isinstance(value, int): total += value
        return total

    def upsert(self, entry: dict, records: list[dict]) -> dict:
        if not records:
            return {"accepted_vertices": 0, "accepted_edges": 0, "errors": []}
        if settings.mock_tigergraph:
            accepted = len(records)
            return {
                "error": False,
                "accepted_vertices": accepted if entry["kind"] == "vertex" else 0,
                "accepted_edges": accepted if entry["kind"] == "edge" else 0,
                "results": [],
                "mock": True,
            }
        payload = self.build_payload(entry, records)
        params = {"vertex_must_exist": "true"} if entry["kind"] == "edge" else None
        with self._client() as client:
            response = client.post(
                f"{self.base}/graph/{settings.graph_name}",
                headers=self.headers,
                params=params,
                content=json.dumps(payload),
            )
            response.raise_for_status()
            data = response.json()
        if data.get("error"):
            raise TigerGraphError(data.get("message") or f"TigerGraph upsert failed for {entry['target']}")
        accepted = self._accepted_count(data, entry["kind"])
        if accepted != len(records):
            raise PartialUpsertError(
                f"TigerGraph accepted {accepted} of {len(records)} requested {entry['kind']} records for {entry['target']}",
                data, accepted, len(records),
            )
        return data

    def run_query(self, query_name: str, params: dict | None = None) -> dict:
        if settings.mock_tigergraph:
            return {"error": False, "results": [], "mock": True, "query": query_name, "params": params or {}}
        with self._client() as client:
            response = client.get(
                f"{self.base}/query/{settings.graph_name}/{query_name}",
                headers=self.headers,
                params=params or {},
            )
            response.raise_for_status()
            data = response.json()
        if data.get("error"):
            raise TigerGraphError(data.get("message") or f"TigerGraph query failed: {query_name}")
        return data

    def statistics(self, kind: str = "vertex", target_type: str = "*") -> dict:
        if kind not in {"vertex", "edge"}:
            raise ValueError("kind must be vertex or edge")
        if settings.mock_tigergraph:
            return {"error": False, "results": [], "mock": True, "kind": kind}
        function = "stat_vertex_number" if kind == "vertex" else "stat_edge_number"
        payload = {"function": function, "type": target_type}
        with self._client() as client:
            response = client.post(
                f"{self.base}/builtins/{settings.graph_name}", headers=self.headers, content=json.dumps(payload)
            )
            response.raise_for_status()
            data = response.json()
        if data.get("error"):
            raise TigerGraphError(data.get("message") or f"TigerGraph builtin failed: {function}")
        return data

    @staticmethod
    def _coerce(value: Any):
        if isinstance(value, (bool, int, float)) or value is None:
            return value
        text = str(value).strip()
        if text.lower() in {"true", "false"}:
            return text.lower() == "true"
        try:
            return int(text)
        except ValueError:
            pass
        try:
            return float(text)
        except ValueError:
            return text
