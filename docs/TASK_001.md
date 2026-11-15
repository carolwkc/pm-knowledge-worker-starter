# Task 001: architecture decisions and verification

## Review and concise implementation plan

The target design supports the product direction, but most of its layers are unnecessary
for the first milestone. Keep one FastAPI process and PostgreSQL; defer object storage,
embeddings, graph infrastructure, model/provider abstractions, agents and connectors.

The actionable gaps were workspace creation, stable source identity, current-version
selection and concurrent version writes. The selected solutions are a development-only
workspace endpoint, source UUIDs in version URLs, latest-version-only retrieval and
transactional row locking. Client-supplied workspace IDs remain explicitly unauthenticated.

Implementation sequence used for Task 001:

1. Scaffold a uv-managed Python 3.12 package and deterministic paragraph chunker;
   test that Unicode text and exact offsets survive ingestion.
2. Migrate the four PostgreSQL tables with Alembic; implement atomic upload/version
   writes, hashing, duplicate detection and source-scoped row locks.
3. Add workspace-filtered keyword search and extractive answers with immutable
   citation IDs, including missing-evidence and isolation tests.
4. Add Docker Compose, synthetic fixtures, curl examples and verification records.

## Architectural decisions

- Store the valid UTF-8 original in PostgreSQL. No artifact store or Markdown renderer
  is needed while inputs are small text files. Hash original bytes; never normalize
  evidence or use extracted source text as instructions.
- Use synchronous SQLAlchemy transactions and explicit migrations. Commit before the
  response; keep source/version/chunk writes atomic. Database uniqueness constraints
  back up the source row lock used for concurrent duplicate and changed uploads.
- Source titles are metadata, not identity. Identical titles can coexist. Identical
  source/hash uploads reuse stable versions; re-uploading a historical hash does not
  restore it as the current version.
- Use PostgreSQL's built-in English lexical search with OR-combined terms and a GIN
  index. Scope and latest-version checks happen in SQL before ranking and limiting.
- Quote up to three ranked chunks with exact source spans. `grounded` means the response
  is extractive, not that the system has reasoned or established the source's truth.
- Use a dedicated test database and real committed transactions, including concurrency
  tests. Clean up only test-created workspaces; never truncate development data.
- Log JSON request summaries without raw paths, query strings, metadata or content.
  Disable Uvicorn access logs in local startup commands.
- Install runtime/development dependencies from `uv.lock`. FastAPI's current test
  client uses `httpx2`; it replaces the deprecated `httpx` test-client dependency.

## Verification record

Executed on macOS arm64 with uv 0.9.24, host Python 3.12.12, Docker Compose v5.1.0
and the `postgres:16.11-bookworm` image. The Docker API image uses Python 3.12.

| Command / check | Outcome |
| --- | --- |
| `uv sync --dev --frozen` | Installed compatible locked dependencies |
| `docker compose up -d --wait db` | Healthy PostgreSQL; separate dev/test databases initialized |
| `uv run alembic upgrade head` | Initial four-table schema applied |
| `uv run alembic check` | No model/migration drift |
| `uv run pytest -q` | 42 tests passed, no skips or warnings |
| `uv run ruff check .` | Passed |
| `uv run ruff format --check .` | Passed |
| `uv run mypy apps/api/src` | Passed, 8 modules |
| `docker compose up -d --build --wait api` | API image built; both services healthy |
| README curl flow against container API | Two fixtures ingested; ranked excerpts and cited answer returned; duplicate reused version 1; missing evidence returned no citations |

Tests cover source-to-answer provenance, original hashes/text/offsets, latest-version
retrieval, historical duplicates, concurrent version numbering, workspace isolation,
instruction-like source text, ranking/limits, upload boundaries, validation and safe
database-unavailable responses. Tests were written before the corresponding behavior;
initial missing-module/migration failures and later validation failures were observed
before passing runs. Final review was an author self-review; no subagent tool was available.

## Remaining limitations

This is a local synthetic-data backend. Workspace filtering is explicit but is not
authentication or authorization; anyone with network access and a workspace UUID can
use that workspace. Production IAM/RBAC, audit/retention/revocation workflows and
deployment hardening remain later work. Original source immutability is enforced by
the append-only API, not database privileges or triggers.

English lexical matching can rank a heading above a useful paragraph or return a
weakly related excerpt for a broad question. There is no semantic recall, contradiction
detection, truth assessment or confidence threshold. A citation identifies an exact
stored span, not an authoritative decision. Direct source browsing and metadata edits
are not implemented. Paragraph chunks have no overlap or semantic structure.

The 1 MiB file limit is checked after multipart parsing; request stream limits and
rate limits need deployment-layer enforcement before public exposure. No real documents,
external models, connectors, frontend or multi-agent orchestration were used. Task 002
has not started. Review this slice before planning the next numbered task.
