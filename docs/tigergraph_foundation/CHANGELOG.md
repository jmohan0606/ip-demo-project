# Changelog

## v0.2.0 — acceptance-gated rebuild

- Replaced the prior GSQL scaffolding with 43 substantive query implementations.
- Added 43 deterministic query invocation cases with required output-key assertions.
- Added query-case validation against sample IDs, enum domains, date ranges and persona authorization paths.
- Added static GSQL semantic validation for edge direction, endpoint types and attributes.
- Added a query audit for parameter use, traversal, aggregation and test coverage.
- Added explicit reverse edges for all 126 directed relationships.
- Added 182 schema-aligned server-side GSQL loading jobs.
- Corrected the RESTPP loader to use manifest column mappings and exact accepted-row counts.
- Added recursive batch isolation, retry, pause/resume, file hashes and checkpoints.
- Added 33 previously absent sample-data targets and ensured every manifest target is nonempty.
- Expanded data to 109,328 rows with all planned personas and scenarios.
- Added AI Ops persona, full CRM status variation, AGP status variation, memory taxonomy and all feedback actions.
- Added Info, Attention, Urgent and Critical coverage for predictions, opportunities and recommendations.
- Added 48 automated business-scenario checks.
- Added full mock ingestion plus unchanged-file reload validation.
- Made live mode the default and mock mode explicitly opt-in.
- Added live installation and RESTPP validation scripts.
- Added package-status, validation and live runbook documentation.
