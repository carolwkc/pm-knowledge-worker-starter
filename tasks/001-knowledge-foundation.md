# Task 001 — Build the first knowledge vertical slice

## Outcome

A locally runnable backend can ingest synthetic Markdown/text product notes and answer simple questions by returning matching evidence with inspectable citations. No external model credentials needed.

## Build

1. Scaffold `apps/api` with a FastAPI application, configuration and tests.
2. Add Docker Compose for a local PostgreSQL database.
3. Add Alembic migrations for workspace, source_document, document_version and source_chunk.
4. Implement simple deterministic text chunking with source span offsets.
5. Implement idempotent document ingestion by hash (same source + unchanged content creates no new version).
6. Add workspace-filtered keyword search, returning ranked chunks.
7. Add `/health`, a simple upload/ingest endpoint, `/search` and `/ask` endpoints. Choose a sensible API prefix and document contracts.
8. `/ask` should return extractive, directly quoted evidence with source references rather than pretending to have an LLM.
9. Add synthetic product notes (e.g. an observability strategy and a decision record) as fixtures.
10. Test ingest → search → ask, no-match behaviour, duplicate upload, and cross-workspace isolation.
11. Document local setup and test commands.

## Constraints

- Stay in this vertical slice; no Next.js app, integrations, external LLM, permissions UI, or multi-agent orchestration in this task.
- Use standard Python patterns and minimal dependencies.
- Server must not expose source excerpts from another workspace.
- Workspace ID supplied by client is only a local development mechanism; mark it as insecure for production.
- Never add sensitive or real company data.

## Done when

- Fresh checkout + documented setup starts the API and database.
- Tests run locally and pass.
- Developer can ingest two fixture documents and retrieve cited excerpts for a sample question.
- Missing evidence produces an explicit status and no fabricated citations.
- README includes curl examples and known security limitations.

## Suggested first sample question

"Why was troubleshooting acceleration prioritised in the first observability release?"
