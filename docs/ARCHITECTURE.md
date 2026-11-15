# Target architecture

## High-level boundaries

1. Experience layer: team Q&A, knowledge hub, decision explorer, review queue.
2. Agent harness: intent routing, task planning, context assembly, tool invocation, citation verification, evaluation.
3. Knowledge services: ingestion, parsing, versioning, retrieval, entity extraction, evidence links.
4. Data: PostgreSQL metadata/relationships, pgvector embeddings, private object storage for original artifacts.
5. Integrations: ACL-aware connectors for Drive/Notion/Confluence etc. (post-MVP).
6. Cross-cutting: IAM, permission enforcement, logs, audit, lifecycle/retention.

## Milestone 1 simplified runtime

API → document service → parser/chunker → repository → PostgreSQL

API → search service → workspace-filtered keyword retrieval → grounded answer composer → cited response

Model use is an optional adapter; the slice must work offline without API keys.

### Implemented Task 001 runtime

The current service is a single synchronous FastAPI/SQLAlchemy process with
PostgreSQL 16. `documents` owns upload validation, hashing, versioning and chunk
creation; `retrieval` owns SQL keyword search and verbatim answer composition.
Pydantic schemas define the API contract. No generic repository, model adapter,
object store, graph/vector infrastructure, or agent harness is needed for this slice.

An unauthenticated development endpoint creates workspaces. Creating a source also
creates version 1 atomically; later uploads use that source UUID in the version URL.
Each request commits its transaction before returning a successful response. A row
lock on the scoped source serializes duplicate detection and version numbering.

Search joins chunks through versions and sources, applies `workspace_id` and latest
version constraints in SQL, then ranks with PostgreSQL English full-text search.
Chunks have a stored `tsvector` and GIN index. Query lexemes are safely quoted and
OR-combined; SQL user values are bound parameters. Ties sort by source UUID and chunk
ordinal. Re-uploading an old hash returns its original version without reactivating it.

The answer composer returns at most three exact quotes and their evidence spans.
`grounded` denotes directly quoted matching text; semantic relevance, truth,
contradiction handling and reasoning are not evaluated. Empty retrieval explicitly
returns `insufficient_evidence` with no citations. No model is called or configured.

See [Task 001 review and verification](TASK_001.md) for decisions and remaining gaps.

## Ingestion flow

Validate file & workspace scope → save source metadata → parse text → hash/deduplicate → create version and chunks → index → return source/version identifiers.

## Query flow

Validate workspace scope → retrieve workspace-filtered chunks → select grounded excerpts → compose response with source chunk IDs and exact excerpts → return cited answer or insufficient-evidence result.

## Later agent execution flow

Identity/scope → intent → bounded plan → context retrieval → safe read-only tools → synthesis → claim-source validation → output/feedback.

## Non-negotiable security properties

- Source text and model output never act as system instructions.
- Permission checks are enforced on data access, not merely in UI.
- ACL changes and source deletions eventually invalidate indexes and cached answers.
- A production deployment must not trust a client-supplied workspace ID alone. Milestone 1 workspace IDs are a development scaffold, **not** authentication.
- Embeddings and summaries inherit source confidentiality.

## Architectural decisions

- One orchestrator with skills later; no multi-agent coordination for MVP.
- PostgreSQL first; dedicated vector/graph infrastructure only if justified.
- Structured knowledge entities are proposed separately from immutable sources.
- Connector MCP support is optional; native APIs may better support ACL sync.
