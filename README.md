# PM Knowledge Worker

An evidence-first product knowledge API for product managers, designers, and tech leads.
Tasks 001–003 provide Markdown/text ingestion, immutable provenance, authenticated
workspace access, keyword/semantic/hybrid search, and deterministic quoted answers.
All supplied content is synthetic. Local CPU embeddings are opt-in; keyword mode
remains the default.

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

## Task 003: provision an identity and workspace access

Every `/api/v1` endpoint requires an issued bearer token. Health, OpenAPI and the
interactive documentation remain public; use **Authorize** in `/docs` to enter a
token. There is no default credential, signup endpoint or authentication bypass.

After starting the API, provision a synthetic user and capture one token receipt
(these examples also require `jq`):

```sh
PMKW_USER_ID=$(docker compose exec -T api uv run --no-sync python -m pmknowledge.auth \
  create-user --name 'Synthetic Aurora member' | jq -er .id)
PMKW_TOKEN_RECEIPT=$(docker compose exec -T api uv run --no-sync python -m pmknowledge.auth \
  issue-token --user-id "$PMKW_USER_ID")
PMKW_API_TOKEN=$(printf '%s' "$PMKW_TOKEN_RECEIPT" | jq -er .token)
PMKW_TOKEN_ID=$(printf '%s' "$PMKW_TOKEN_RECEIPT" | jq -er .id)

curl --fail --silent --show-error http://localhost:8000/api/v1/me \
  -H "Authorization: Bearer $PMKW_API_TOKEN" | jq
```

Only token issuance returns plaintext; keep the receipt private and retain its token
ID for revocation. The database stores a SHA-256 digest of a secret generated from
32 random bytes. Tokens expire after 30 days by default; `issue-token` accepts a
positive `--expires-in-days`. Create a fresh token to rotate, then use the operator
command `revoke-token --token-id TOKEN_UUID` with the retired token's recorded ID.

On the host, use the same commands with `uv run python -m pmknowledge.auth`, omitting
the Docker prefix and `--no-sync`. Provisioning commands are trusted operator tools
using database credentials; they are not available through HTTP. They print JSON
only after committing, and failures return a nonzero exit status.

An authenticated user can create a workspace and becomes its first owner atomically.
`GET /api/v1/workspaces` lists only workspaces the caller has joined, including their
role. All documents in a workspace inherit that workspace's access:

| Role | Access |
| --- | --- |
| `reader` | Search and ask |
| `editor` | Reader access plus uploads and source versions |
| `owner` | Editor access plus listing, granting, changing and removing memberships |

Owners manage already provisioned users through `/members/{user_id}` (see the API
table below). They can promote another owner before removing/demoting themselves.
The last owner cannot be removed or demoted, including during concurrent requests.

Migration `0003` preserves all existing evidence and embeddings. Existing workspaces
start without memberships and remain inaccessible until an operator assigns an owner:

```sh
docker compose exec -T api uv run --no-sync python -m pmknowledge.auth \
  grant-owner --workspace-id "$WORKSPACE_ID" --user-id "$PMKW_USER_ID"
```

The command is idempotent. Do not delete existing database volumes to upgrade.
Revocations and membership changes apply to the next request; requests already
underway may finish. API tokens confer no workspace access without membership.

## Try the synthetic source-to-answer flow

These examples additionally use `curl` and `jq`. The URI is inert metadata and is never fetched.

```sh
WORKSPACE_ID=$(curl --fail --silent --show-error http://localhost:8000/api/v1/workspaces \
  -H "Authorization: Bearer $PMKW_API_TOKEN" \
  -H 'Content-Type: application/json' -d '{"name":"Synthetic Aurora team"}' | jq -er .id)

SOURCE_ID=$(curl --fail --silent --show-error \
  "http://localhost:8000/api/v1/workspaces/$WORKSPACE_ID/sources" \
  -H "Authorization: Bearer $PMKW_API_TOKEN" \
  -F 'title=Observability strategy (synthetic)' \
  -F 'external_uri=https://example.invalid/observability-strategy' \
  -F 'file=@apps/api/tests/fixtures/observability-strategy.md' | jq -er .source_document_id)

curl --fail --silent --show-error \
  "http://localhost:8000/api/v1/workspaces/$WORKSPACE_ID/sources" \
  -H "Authorization: Bearer $PMKW_API_TOKEN" \
  -F 'title=First release decision (synthetic)' \
  -F 'file=@apps/api/tests/fixtures/observability-decision.txt' | jq

curl --fail --silent --show-error --get \
  "http://localhost:8000/api/v1/workspaces/$WORKSPACE_ID/search" \
  -H "Authorization: Bearer $PMKW_API_TOKEN" \
  --data-urlencode 'q=troubleshooting acceleration' --data-urlencode 'limit=5' | jq

curl --fail --silent --show-error \
  "http://localhost:8000/api/v1/workspaces/$WORKSPACE_ID/ask" \
  -H "Authorization: Bearer $PMKW_API_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"question":"Why was troubleshooting acceleration prioritised in the first observability release?"}' | jq

# Identical content for the same source: HTTP 200, duplicate=true, unchanged version/chunk IDs.
curl --fail --silent --show-error \
  "http://localhost:8000/api/v1/workspaces/$WORKSPACE_ID/sources/$SOURCE_ID/versions" \
  -H "Authorization: Bearer $PMKW_API_TOKEN" \
  -F 'file=@apps/api/tests/fixtures/observability-strategy.md' | jq

# No matching terms: status=insufficient_evidence and sources=[].
curl --fail --silent --show-error \
  "http://localhost:8000/api/v1/workspaces/$WORKSPACE_ID/ask" \
  -H "Authorization: Bearer $PMKW_API_TOKEN" \
  -H 'Content-Type: application/json' -d '{"question":"nonexistentplatypus"}' | jq
```

The answer is labelled `Extracted evidence (verbatim source text)` and includes exact
quotes such as `Troubleshooting acceleration is the priority ... because engineers
spend too long correlating logs during incidents.` It does not infer a new conclusion.

## API contracts

| Method / path | Input | Result |
| --- | --- | --- |
| `GET /health` | None | `200 {"status":"ok"}` when the database is reachable; `503` otherwise |
| `GET /api/v1/me` | Bearer token | `200 {id, name, created_at}` for the current user |
| `GET /api/v1/workspaces` | Bearer token | `200 {workspaces:[{id, name, created_at, role}]}` for joined workspaces only |
| `POST /api/v1/workspaces` | JSON `{"name":"..."}` | `201 {id, name, created_at}`; caller becomes owner |
| `GET /api/v1/workspaces/{workspace_id}/members` | Owner token | `200 {members:[{user_id, role}]}` |
| `PUT /api/v1/workspaces/{workspace_id}/members/{user_id}` | Owner token, JSON `{"role":"reader"}` (or `editor`, `owner`) | `200 {user_id, role}`; creates or updates membership |
| `DELETE /api/v1/workspaces/{workspace_id}/members/{user_id}` | Owner token | `204`; unknown target/membership `404`; final-owner removal `409` |
| `POST /api/v1/workspaces/{workspace_id}/sources` | Multipart `file`, `title`, optional `external_uri` | `201` ingestion receipt |
| `POST /api/v1/workspaces/{workspace_id}/sources/{source_id}/versions` | Multipart `file` | `201` new version or `200` existing identical version |
| `GET /api/v1/workspaces/{workspace_id}/search` | Query `q`, optional `limit` (default 5, range 1–20), `mode` | `200 {results:[...]}` ranked excerpts |
| `POST /api/v1/workspaces/{workspace_id}/ask` | JSON `{question, limit?, mode?}` | `200 {answer, status, sources}`; at most three quoted citations |

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

Keyword search uses English stemming and stop words, matches any query term, and ranks only
the latest version of each source. Empty workspaces, stop-word-only, punctuation-only,
and unmatched retrieval return no results. `grounded` means matching text was quoted;
it does not guarantee the excerpts fully answer the question or that the source is
factually correct. No matches return `insufficient_evidence` and no citations.

Source IDs define upload identity; duplicate titles are allowed. To update a source,
reuse its ID through the versions endpoint. Re-uploading any previously seen hash
returns the original version without changing which version is current. Metadata is
set when a source is created. Missing/inaccessible workspaces and sources outside
the requested workspace return `404`; malformed requests return `422`. Missing,
malformed, unknown, expired or revoked credentials return `401` with a Bearer
challenge. Members lacking the required role receive `403`. Removing/demoting the
final owner returns `409`.

## Task 002: enable local semantic and hybrid retrieval

`mode` accepts `keyword` (default), `semantic`, or `hybrid`. Every mode filters by the
workspace and latest source version before ranking. Semantic search uses exact cosine
ranking with `BAAI/bge-small-en-v1.5` (384 dimensions, English, CPU). Hybrid combines
the top 20 keyword and top 20 semantic candidates using reciprocal rank fusion
(`sum(1 / (60 + rank))`), deduplicates chunks, and then applies `limit`.

The pgvector-capable PostgreSQL 16 image uses the existing database volume. Migration
`0002` enables the vector extension and adds a separate derived-embedding table;
original source text, chunks and citations stay unchanged. Do not delete a volume
to upgrade. Enabling the extension requires database-owner/superuser permission in
this local setup. No approximate vector index is needed at this size.

For Docker, run the normal setup above, then explicitly download the public model:

```sh
docker compose run --rm --no-deps -e HF_HUB_OFFLINE=0 api \
  uv run --no-sync python -m pmknowledge.embeddings download
```

This command contacts the model registry to download about 67 MB of public weights;
it sends no documents. Set `EMBEDDINGS_ENABLED=true` in `.env`, then recreate the API:

```sh
docker compose up -d --wait api
```

Weights are cached in the `embedding_models` volume. Normal API requests use local
files only, and the container additionally sets `HF_HUB_OFFLINE=1`. No model is
downloaded during API requests, ingestion, backfill or evaluation. With embeddings
enabled, new ingests embed their chunks in the same transaction. A model failure
rolls back the source/version/chunk writes and returns a safe `503`.

Existing sources need an explicit workspace-scoped backfill (reuse `WORKSPACE_ID`
from the curl demo):

```sh
docker compose exec api uv run --no-sync python -m pmknowledge.embeddings backfill \
  --workspace-id "$WORKSPACE_ID"

curl --fail --silent --show-error --get \
  "http://localhost:8000/api/v1/workspaces/$WORKSPACE_ID/search" \
  --data-urlencode 'q=How can engineers find problems sooner to shorten outages?' \
  -H "Authorization: Bearer $PMKW_API_TOKEN" \
  --data-urlencode 'mode=semantic' | jq

curl --fail --silent --show-error \
  "http://localhost:8000/api/v1/workspaces/$WORKSPACE_ID/ask" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $PMKW_API_TOKEN" \
  -d '{"question":"troubleshooting acceleration","mode":"hybrid"}' | jq
```

Backfill only indexes the requested workspace's latest versions and skips existing
model/chunk pairs. Repeating it is idempotent. Until backfill completes, semantic
search covers only chunks with embeddings; hybrid can still retrieve unindexed
chunks through its keyword component. Keyword mode works with embeddings disabled.
Explicit semantic/hybrid requests return `503` if embeddings are disabled or the
local model is unavailable; the API never silently switches retrieval mode.

On the host, use the same commands through `uv run` without `docker compose exec api`
or `--no-sync`. Download once with `uv run python -m pmknowledge.embeddings download`,
then enable embeddings when starting Uvicorn. The host cache defaults to
`.cache/embeddings`; override it with `EMBEDDING_CACHE_DIR`. Host and Docker caches
are separate. Neither cache belongs in Git.

`SEMANTIC_MIN_SCORE` defaults to `0.6` and only gates cosine similarity candidates.
Scores are mode-specific ranking values: keyword rank, cosine similarity, or RRF
score. They are not comparable across modes and are not confidence estimates.
Broad lexical matches may still enter hybrid answers even if semantically irrelevant.

## Retrieval evaluation

Eight synthetic documents have eight labelled positive questions and two unrelated
questions in `apps/api/evaluation/cases.json`. Run from the repository root after
migration and the explicit model download:

```sh
uv run python -m pmknowledge.evaluation --k 3
# Or use the cached model inside Docker:
docker compose exec api uv run --no-sync python -m pmknowledge.evaluation --k 3
```

The command reports document recall@k, mean reciprocal rank@k for positive cases,
and no-evidence accuracy separately for the unrelated cases. It exercises the real
local model and SQL retrievers in an isolated temporary workspace, then rolls back
all fixture data. It does not publish sources or modify existing workspaces.

Recorded results and limitations are in [Task 002 verification](docs/TASK_002.md).
These tiny synthetic measurements are not evidence that later pilot quality targets
have been achieved. Ties use source UUIDs, so MRR can vary across fresh evaluation
workspaces when hybrid candidates have equal scores.

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
commit real transactions (including concurrent uploads/membership changes), and clean
up only their synthetic users/workspaces and temporary migration schemas. They never
truncate the development database. If the volume predates the
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

Local API tokens authenticate callers and database memberships authorize workspace
access. User IDs, role headers and workspace UUIDs alone confer no permissions.
Both SQL retrievers require membership before ranking. Every source and derived
embedding in a workspace has the same confidentiality boundary; document ACLs are
not implemented. Operators with database credentials retain unrestricted access.

This remains a local synthetic-data service. There is no SSO, password login,
production identity lifecycle, TLS termination, rate limiting, request-stream size enforcement,
retention/deletion workflow, backup policy, encryption setup, or production deployment
configuration. The file limit is checked after multipart parsing, which can spool a
larger incoming body to disk. Database credentials are public local defaults.

Application logs include route templates, status, and duration; they omit document
contents, metadata, and queries. Uvicorn access logging is disabled in documented
commands because URL query strings can contain question text. Treat source excerpts
and Markdown as untrusted text if a UI is added; no source instruction is executed.

No external model API, connector, frontend, agent orchestration, or external write
action is implemented. Retrieval does not detect contradictions or evaluate whether
an excerpt supports an interpretation. The local embedding model is English-only
and truncates model inputs at 512 tokens; character-based chunks are not token-aware.
The model name and Python dependencies are fixed for this slice; stronger weight
revision pinning and representative threshold calibration remain future work.
Task 003 implementation details and verification are in [Task 003](docs/TASK_003.md).
