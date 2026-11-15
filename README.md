# PM Knowledge Worker

An evidence-first product knowledge API for product managers, designers, and tech leads.
Task 001 provides Markdown/text ingestion, immutable provenance, workspace-scoped
keyword search, and deterministic quoted answers. All supplied content is synthetic.

## Run locally

Requires Docker with Compose v2+. Run commands from the repository root:

```sh
# First run only; keep an existing .env if you have already configured one.
cp .env.example .env
docker compose up -d --build --wait
curl --fail http://localhost:8000/health
```

The API runs at <http://localhost:8000>; interactive contracts are at
<http://localhost:8000/docs>. Compose waits for PostgreSQL and runs `alembic upgrade head`
before starting the API. The image runs as a non-root user and installs only runtime
dependencies from `uv.lock`. Both services bind to `127.0.0.1`.

Compose requires `POSTGRES_PASSWORD` in `.env` or the shell environment; the API
refuses to start if it is empty. There is no password fallback in Compose. Start with
`.env.example` for local development and edit `.env` to customize it.
`POSTGRES_PASSWORD`, `POSTGRES_PORT`, and `API_PORT`
configure Compose; `DATABASE_URL` configures the API when run on the host. Keep host
URLs consistent with any changed port/password (URL-encode special characters in
passwords). Changing a password does not update an already initialized database.
Inside Compose, the API URL omits the password; psycopg reads it from `PGPASSWORD`,
which uses the same `POSTGRES_PASSWORD` value as the database container.

To run the API on the host instead, install [uv](https://docs.astral.sh/uv/), then:

```sh
uv python install 3.12
uv sync --dev --frozen
docker compose up -d --wait db
uv run alembic upgrade head
uv run uvicorn pmknowledge.main:app --reload --host 127.0.0.1 --no-access-log
```

Stop the container API first (`docker compose stop api`) if using the same port.
No schema is created implicitly by application startup. Outside Compose, migrations
are an explicit step. `docker compose down` stops services and preserves the data volume.

## Try the synthetic source-to-answer flow

These examples additionally use `curl` and `jq`. The URI is inert metadata and is never fetched.

```sh
WORKSPACE_ID=$(curl --fail --silent --show-error http://localhost:8000/api/v1/workspaces \
  -H 'Content-Type: application/json' -d '{"name":"Synthetic Aurora team"}' | jq -er .id)

SOURCE_ID=$(curl --fail --silent --show-error \
  "http://localhost:8000/api/v1/workspaces/$WORKSPACE_ID/sources" \
  -F 'title=Observability strategy (synthetic)' \
  -F 'external_uri=https://example.invalid/observability-strategy' \
  -F 'file=@apps/api/tests/fixtures/observability-strategy.md' | jq -er .source_document_id)

curl --fail --silent --show-error \
  "http://localhost:8000/api/v1/workspaces/$WORKSPACE_ID/sources" \
  -F 'title=First release decision (synthetic)' \
  -F 'file=@apps/api/tests/fixtures/observability-decision.txt' | jq

curl --fail --silent --show-error --get \
  "http://localhost:8000/api/v1/workspaces/$WORKSPACE_ID/search" \
  --data-urlencode 'q=troubleshooting acceleration' --data-urlencode 'limit=5' | jq

curl --fail --silent --show-error \
  "http://localhost:8000/api/v1/workspaces/$WORKSPACE_ID/ask" \
  -H 'Content-Type: application/json' \
  -d '{"question":"Why was troubleshooting acceleration prioritised in the first observability release?"}' | jq

# Identical content for the same source: HTTP 200, duplicate=true, unchanged version/chunk IDs.
curl --fail --silent --show-error \
  "http://localhost:8000/api/v1/workspaces/$WORKSPACE_ID/sources/$SOURCE_ID/versions" \
  -F 'file=@apps/api/tests/fixtures/observability-strategy.md' | jq

# No matching terms: status=insufficient_evidence and sources=[].
curl --fail --silent --show-error \
  "http://localhost:8000/api/v1/workspaces/$WORKSPACE_ID/ask" \
  -H 'Content-Type: application/json' -d '{"question":"nonexistentplatypus"}' | jq
```

The answer is labelled `Extracted evidence (verbatim source text)` and includes exact
quotes such as `Troubleshooting acceleration is the priority ... because engineers
spend too long correlating logs during incidents.` It does not infer a new conclusion.

## API contracts

| Method / path | Input | Result |
| --- | --- | --- |
| `GET /health` | None | `200 {"status":"ok"}` when the database is reachable; `503` otherwise |
| `POST /api/v1/workspaces` | JSON `{"name":"..."}` | `201 {id, name, created_at}`; unauthenticated development operation |
| `POST /api/v1/workspaces/{workspace_id}/sources` | Multipart `file`, `title`, optional `external_uri` | `201` ingestion receipt |
| `POST /api/v1/workspaces/{workspace_id}/sources/{source_id}/versions` | Multipart `file` | `201` new version or `200` existing identical version |
| `GET /api/v1/workspaces/{workspace_id}/search` | Query `q`, optional `limit` (default 5, range 1–20) | `200 {results:[...]}` ranked excerpts |
| `POST /api/v1/workspaces/{workspace_id}/ask` | JSON `{question, limit?}` | `200 {answer, status, sources}`; at most three quoted citations |

Ingestion receipts contain `workspace_id`, `source_document_id`, `document_version_id`,
`version_number`, `sha256`, `chunk_count`, and `duplicate`. Names/titles have a 200-character
limit; questions/queries have a 1,000-character limit. Blank values and NUL characters
are rejected. Uploads accept non-empty UTF-8 `.md`, `.markdown`, and `.txt` files up to
1 MiB; invalid text is `422`, oversized files `413`, and unsupported extensions `415`.

Each search hit contains source/version/chunk UUIDs, `title`, `external_uri`, zero-based
`ordinal`, `excerpt`, `start_char`, `end_char`, and `score`. Offsets are zero-based Python
Unicode character offsets, end-exclusive, into the version's unchanged `plain_text`.
Markdown syntax and line endings remain intact. Citation objects contain the same
evidence fields except `score`, plus a string `citation` number matching `[1]` in `answer`.

Search uses English stemming and stop words, matches any query term, and ranks only
the latest version of each source. Empty workspaces, stop-word-only, punctuation-only,
and unmatched retrieval return no results. `grounded` means matching text was quoted;
it does not guarantee the excerpts fully answer the question or that the source is
factually correct. No matches return `insufficient_evidence` and no citations.

Source IDs define upload identity; duplicate titles are allowed. To update a source,
reuse its ID through the versions endpoint. Re-uploading any previously seen hash
returns the original version without changing which version is current. Metadata is
set when a source is created. Missing workspaces and sources outside the requested
workspace return `404`; malformed requests return `422`.

## Tests and checks

Requires uv and the Compose database. The database container initializes two databases
on its first run: `pmknowledge` for development and `pmknowledge_test` for tests.

```sh
uv sync --dev --frozen
docker compose up -d --wait db
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy apps/api/src
uv run alembic check
```

`alembic check` expects the development database to be migrated first, either by Compose
or `uv run alembic upgrade head`. Tests run Alembic against the test database automatically,
commit real transactions (including concurrent uploads), and remove only workspaces
they created. They never truncate the development database. If the volume predates the
test database initializer, create it without deleting development data:

```sh
docker compose exec db createdb -U pmknowledge pmknowledge_test
```

For a different test database, export a URL whose database name ends in `_test`:

```sh
TEST_DATABASE_URL=postgresql+psycopg://pmknowledge:localdev@localhost:5432/pmknowledge_test uv run pytest
```

Database-free tests: `uv run pytest -m 'not integration'`. The full suite fails if
PostgreSQL is unavailable; integration tests are never silently skipped.

See [Task 001 decisions and verification](docs/TASK_001.md) for the architecture review,
implementation sequence, and recorded outcomes.

## Security limitations

Workspace IDs are client-supplied development scaffolding, **not authentication**.
Anyone who can reach this API can create workspaces and query or modify a known
workspace. SQL scopes prevent accidental cross-workspace results but do not authorize
the caller. Do not expose this service publicly or use confidential data.

There is no production IAM/RBAC, rate limiting, request-stream size enforcement,
retention/deletion workflow, backup policy, encryption setup, or production deployment
configuration. The file limit is checked after multipart parsing, which can spool a
larger incoming body to disk. Database credentials are public local defaults.

Application logs include route templates, status, and duration; they omit document
contents, metadata, and queries. Uvicorn access logging is disabled in documented
commands because URL query strings can contain question text. Treat source excerpts
and Markdown as untrusted text if a UI is added; no source instruction is executed.

No external model, connector, frontend, agent orchestration, or external write action
is implemented. Keyword retrieval does not detect contradictions or evaluate whether
an excerpt supports an interpretation. Task 002 has not started.
