# Final React UI Runbook

## Backend

```bash
uv run python run_local_api.py
```

## Frontend

```bash
cd frontend
npm install
npm run validate:final-ui
npm run dev
```

Open:

```text
http://localhost:3000
```

## Full UI Validation

```bash
cd frontend
npm run validate:all-ui
```

## Org Artifactory npm Registry

Create `frontend/.npmrc` before install:

```text
registry=https://<artifactory-host>/artifactory/api/npm/<repo-name>/
always-auth=true
//<artifactory-host>/artifactory/api/npm/<repo-name>/:_authToken=<token>
```

## Next Step

Part 13.18 — Final UI Runtime Build Validation & Screenshot Review.
