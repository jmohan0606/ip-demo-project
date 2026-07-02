# React UI Quick Start

## Backend

```bash
uv run python run_local_api.py
```

## Frontend

```bash
cd frontend
npm install
npm run validate:ui
npm run dev
```

Open:

```text
http://localhost:3000
```

## Org Artifactory npm Registry

Create `frontend/.npmrc` before install:

```text
registry=https://<artifactory-host>/artifactory/api/npm/<repo-name>/
always-auth=true
//<artifactory-host>/artifactory/api/npm/<repo-name>/:_authToken=<token>
```
