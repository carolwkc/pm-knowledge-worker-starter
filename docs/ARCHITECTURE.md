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
