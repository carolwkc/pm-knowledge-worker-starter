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

Task 001 initially exposed an unauthenticated development endpoint to create workspaces;
Task 003 replaces this with authenticated ownership. Creating a source also
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

### Task 002 local retrieval extension

An opt-in CPU encoder generates 384-dimensional English embeddings from cached
public model weights. Only the explicit download CLI may retrieve weights; runtime
model loading uses local files only. Enabled ingestion stores derived embeddings
atomically alongside new chunks. A workspace-scoped, repeatable CLI backfills older
sources. Original evidence is unchanged.

The same search/ask API accepts keyword (default), semantic, or hybrid mode. Semantic
retrieval uses exact pgvector cosine ranking above a configurable similarity floor.
Hybrid merges up to 20 workspace-filtered candidates per retriever using reciprocal
rank fusion (k=60). Explicit semantic/hybrid requests fail safely if inference is
disabled/unavailable. Answer composition remains deterministic quotation.

Synthetic evaluation reports positive recall/MRR and unrelated-question abstention
separately, with temporary fixture data rolled back. Lexical false positives remain
possible in hybrid mode; similarity and fusion scores do not establish claim support.
See [Task 002 verification](TASK_002.md) for measured results and tradeoffs.

### Task 003 authenticated workspace access

All `/api/v1` routes share a mandatory HTTP bearer dependency, which looks up a
SHA-256 token digest, expiry and revocation state in PostgreSQL on each request.
Only health and schema/documentation routes remain public. Authenticated identity
comes from the token and is passed explicitly into ingestion, search and answer
services; user/role headers do not establish identity.

Workspace creation commits an initial owner in the same transaction. Memberships
grant reader, editor or owner access to the entire workspace. Service-level checks
precede source processing and inference. Both keyword and vector SQL require the
user's membership as well as workspace/latest-version predicates before ranking and
limits. No permission or answer cache needs invalidation in this slice.

Membership writers lock the workspace, recheck the acting owner's role after the
lock, and preserve at least one owner. Permission changes affect subsequent requests;
in-flight requests may finish. Missing and inaccessible workspaces both return 404,
while members lacking the required role receive 403. Credential failures return 401
with a Bearer challenge; authentication never falls back when the database fails.

The local CLI provisions users, issues/revokes tokens and assigns owners using trusted
database credentials. Original workspaces receive no automatic owner during migration.
Backfill remains an operator operation; evaluation creates a synthetic identity and
membership inside its rolled-back fixture transaction. See [Task 003](TASK_003.md).

### Task 004 decision review

Editors explicitly request extraction from a specified latest source version.
The deterministic `decision-marker-v1` rule selects unchanged source chunks;
proposals are stored separately from evidence and never execute source instructions.
Owners approve/reject immutable quotations, including their own proposals. A single
transaction stores the terminal review and, on approval, one decision record.

Generation acquires a workspace key-share lock before its source update lock, matching
the order of explicit locks and foreign-key checks. It rechecks editor access after waiting.
Review locks workspace → source → proposal, rechecks acting ownership after the
workspace lock, and checks freshness after the source lock. This serializes review
against membership writers, other reviews and concurrent version ingestion. Stale
pending approvals fail with 409. Rejections and same-action terminal retries retain
history; previously approved records expose a computed source freshness flag.

Members read decisions; editors/owners also read proposal queues. Every service
requires identity and workspace access and scopes its data joins to that workspace.
Search/ask remain independent of this derived review layer. No external model, frontend,
automatic promotion, source mutation or external write is introduced.

### Task 005 web experience

React/TypeScript assets are built with Vite in a separate Node Docker stage and
served at `/` and `/assets` by the existing FastAPI process. `WEB_DIST_DIR` is
optional for API-only host operation; configured invalid builds fail at startup.
Development uses Vite's local `/api` proxy, without broad CORS or a catch-all route.

The browser validates an operator-issued token, lists joined workspaces and asks
through the existing retrieval API. Tokens and current question/evidence remain
only in memory. Scope/session changes abort work and invalidate response generations
so delayed successes or failures cannot restore old data. Access errors clear
evidence and refresh workspace discovery; credential errors clear the session.

A reader-authorised source/version read joins through the requested workspace and
membership before returning original text and computed freshness in one query.
Historical versions remain accessible. The source viewer validates version identity
and exact Unicode code-point spans, preserving CRLF before slicing; only verified
quotes receive a highlight. All document/answer/URI content remains inert text.
Authenticated API responses, including failures, use no-store cache headers.

### Task 009 explicit Q&A feedback

Ordinary ask calls still return ephemeral deterministic quotations. Explicit member
feedback submission saves user-reported question/mode/answer context in a separate
workspace-scoped record. Source joins validate all citation identities, metadata,
text and offsets, and the shared pure quotation composer validates answer formatting.
This checks citation integrity, not whether this response was issued for the question.

Only owners list/read feedback. Authenticated authors and atomic unique submission
identifiers provide safe same-payload retries without exposing anyone else's records.
No question history, external inference, knowledge promotion or resolution workflow is
introduced. Browser generation guards/cancellation protect scope; uncertain writes
retain their frozen submission and require an explicit retry. Feedback snapshots
persist until workspace deletion and do not depend on the continued existence of
original source rows. Original-version navigation still enforces current membership.

## Ingestion flow

Authenticate user → verify editor/owner membership → validate file & workspace scope → save source metadata → parse text → hash/deduplicate → create version and chunks → index → return source/version identifiers.

## Query flow

Authenticate user → verify workspace membership → retrieve permission-filtered chunks → select grounded excerpts → compose response with source chunk IDs and exact excerpts → return cited answer or insufficient-evidence result.

## Later agent execution flow

Identity/scope → intent → bounded plan → context retrieval → safe read-only tools → synthesis → claim-source validation → output/feedback.

## Non-negotiable security properties

- Source text and model output never act as system instructions.
- Permission checks are enforced on data access, not merely in UI.
- ACL changes and source deletions eventually invalidate indexes and cached answers.
- A workspace UUID alone never authorizes access. Task 003 checks bearer credentials and membership; production SSO and identity lifecycle remain deferred.
- Embeddings and summaries inherit source confidentiality.

## Architectural decisions

- One orchestrator with skills later; no multi-agent coordination for MVP.
- PostgreSQL first; dedicated vector/graph infrastructure only if justified.
- Structured knowledge entities are proposed separately from immutable sources.
- Connector MCP support is optional; native APIs may better support ACL sync.
