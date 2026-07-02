# Part 13.18 — Final UI Runtime Build Validation & Screenshot Review

## Added

- Final UI runtime route validation script
- Screenshot review checklist generator
- Optional Playwright screenshot capture setup
- Final screenshot test file for all enterprise routes
- Final UI runtime documentation

## Validate Without Browser

```bash
cd frontend
npm run validate:runtime
npm run validate:screenshot-checklist
```

## Runtime Build Validation

```bash
cd frontend
npm install
npm run validate:final-ui
npm run validate:runtime
npm run build
```

## Start UI

```bash
cd frontend
npm run dev
```

## Optional Screenshot Capture

In another terminal, after the app is running:

```bash
cd frontend
npx playwright install chromium
npm run screenshots
```

Screenshots are saved to:

```text
docs/ui_runtime/screenshots/
```

## Important

This package provides screenshot automation and review readiness. Actual screenshots must be captured in the user's local machine after installing npm dependencies and running the frontend.
