from __future__ import annotations

import json

from app.graph.tigergraph_production_runtime import get_tigergraph_production_runtime


def main() -> None:
    runtime = get_tigergraph_production_runtime()
    result = runtime.activate_smoke_test()
    print(json.dumps(result, indent=2))
    # Passing in mock mode is allowed for local validation; production_data_active
    # must be true for production cutover.
    if result["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
