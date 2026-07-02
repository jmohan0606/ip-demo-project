# TigerGraph RESTPP Corrected Audit

## What was wrong

The previous REST fallback was too generic and unsafe:

- It assumed `TIGERGRAPH_HOST` was already the RESTPP base URL.
- It did not clearly support `TG_HOST + TG_RESTPP_PORT`.
- It did not distinguish cloud/proxied endpoints from local RESTPP ports.
- It had weak support for `TG_API_TOKEN`, `TG_JWT_TOKEN`, and `TIGERGRAPH_TOKEN`.
- It did not expose a RESTPP ping/smoke-test path.
- It did not allow GET vs POST installed-query execution.

## Corrected RESTPP behavior

### Base URL resolution order

1. `TIGERGRAPH_RESTPP_URL`, if provided.
2. `TG_HOST` / `TIGERGRAPH_HOST`.
3. If no port and not `TG_TGCLOUD=true`, append `TG_RESTPP_PORT`.
4. If the host already contains `/restpp`, do not mutate it.

### Installed query endpoint

```text
GET  {restpp_base}/query/{graph}/{query_name}?param=value
POST {restpp_base}/query/{graph}/{query_name}
```

Controlled by:

```text
TIGERGRAPH_REST_QUERY_METHOD=GET
```

or:

```text
TIGERGRAPH_REST_QUERY_METHOD=POST
```

### Graph upsert endpoint

```text
POST {restpp_base}/graph/{graph}
```

Vertex payload:

```json
{
  "vertices": {
    "Advisor": {
      "ADV0001": {
        "name": "Alex Morgan"
      }
    }
  }
}
```

Edge payload:

```json
{
  "edges": {
    "Advisor": {
      "ADV0001": {
        "SERVES_HOUSEHOLD": {
          "Household": {
            "HH001": {}
          }
        }
      }
    }
  }
}
```

### Auth headers

Supported:

```text
TG_JWT_TOKEN -> Authorization: Bearer <jwt>
TG_API_TOKEN -> Authorization: Bearer <token>
TIGERGRAPH_TOKEN -> Authorization: Bearer <token>
```

## Validation

```bash
uv run python scripts/validate_tigergraph_restpp_corrected.py
uv run python scripts/tigergraph_restpp_smoke_test.py
```

## Recommendation

For production fallback, explicitly set:

```text
TIGERGRAPH_REST_ENABLED=true
TIGERGRAPH_RESTPP_URL=https://<your-restpp-endpoint>
TG_GRAPHNAME=iPerformInsights
TG_API_TOKEN=<token>
```

For local TigerGraph:

```text
TIGERGRAPH_REST_ENABLED=true
TG_HOST=http://127.0.0.1
TG_RESTPP_PORT=9000
TG_GRAPHNAME=iPerformInsights
TG_USERNAME=tigergraph
TG_PASSWORD=tigergraph
```
