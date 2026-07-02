from __future__ import annotations

import json
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

BASE_URL = "http://127.0.0.1:8000"

ENDPOINTS = [
    ("GET", "/health", None),
    ("GET", "/graph-runtime/status", None),
    ("GET", "/knowledge-runtime/status", None),
    ("GET", "/feature-runtime/status", None),
    ("GET", "/recommendation-runtime/status", None),
    ("GET", "/memory-runtime/status", None),
    ("GET", "/llm-activation/status", None),
    ("GET", "/tigergraph-activation/status", None),
    ("POST", "/orchestration/run", {
        "workflow": "dashboard",
        "persona": "Advisor",
        "scope_type": "Advisor",
        "scope_id": "ADV0001",
        "period": "YTD",
        "compare_to": "Prior Year",
        "input_payload": {}
    }),
]


def call(method: str, path: str, payload):
    url = BASE_URL + path
    body = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
    req = Request(url, data=body, headers=headers, method=method)
    start = time.time()
    try:
        with urlopen(req, timeout=8) as response:
            data = response.read().decode("utf-8")
            return {
                "endpoint": path,
                "method": method,
                "status": "passed",
                "http_status": response.status,
                "duration_ms": round((time.time() - start) * 1000),
                "response_preview": data[:500],
            }
    except Exception as exc:
        return {
            "endpoint": path,
            "method": method,
            "status": "failed",
            "error": str(exc),
            "duration_ms": round((time.time() - start) * 1000),
        }


def main() -> None:
    results = [call(method, path, payload) for method, path, payload in ENDPOINTS]
    report = {
        "status": "passed" if all(r["status"] == "passed" for r in results) else "failed",
        "base_url": BASE_URL,
        "results": results,
    }
    print(json.dumps(report, indent=2))
    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
