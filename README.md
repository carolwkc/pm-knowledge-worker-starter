# PM Knowledge Worker

An evidence-first product knowledge API for product managers, designers, and tech leads.
Tasks 001–006 provide Markdown/text ingestion, immutable provenance, authenticated
workspace access, keyword/semantic/hybrid search, deterministic quoted answers,
explicitly reviewed decision quotations, web Q&A with source navigation, and a
source catalogue with title filtering and version history.
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

The web UI runs at <http://localhost:8000>; interactive API contracts are at
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
| `reader` | Search, ask and read approved decisions |
| `editor` | Reader access plus uploads, source versions and generating/inspecting proposals |
| `owner` | Editor access plus approving/rejecting proposals and managing memberships |

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

## Task 005: ask and inspect evidence in the browser

The normal Docker image includes the web build; no Node installation is needed to
run it. After provisioning a token and uploading the synthetic fixtures above, open
<http://localhost:8000>, enter the token and choose **Connect**. The first workspace
you have joined is selected automatically. Ask the sample question in keyword mode,
then choose a numbered source citation to inspect the original text.

Answers remain deterministic quotations, not generated reasoning. The source panel
shows the exact cited version and highlights only a verified matching character
span. A **Historical version** label means newer source content exists; it does not
replace the citation. Expand **Source details** for source/version/chunk IDs, offsets,
ingestion time, hash and inert external URI metadata. Source text is never rendered
as HTML or interpreted as instructions.

Tokens, questions and answers stay in tab memory, without browser storage or saved
history. **Disconnect** and page reload clear the session. Changing workspaces clears
the current question/evidence; revoked credentials require reconnecting. An access
failure refreshes the available workspace list. Content already received cannot be
retracted until a request detects a permission change or the session is cleared.
There is no default token, signup, upload screen or membership administration UI.
Keep using the existing operator commands and APIs for those operations.

Semantic/hybrid modes use the same opt-in local embeddings as the API. If unavailable,
the UI reports that mode's failure and lets you select keyword; it never switches
silently. No external model is called. The local deployment is loopback-only; this
slice does not provide production SSO, TLS termination or a full identity lifecycle.

## Task 006: browse original sources and version history

Connect with an existing token, select a workspace, then choose **Browse sources**.
Readers, editors and owners see the same workspace-wide source catalogue. Each row
shows its title, latest version number and ingestion timestamp. Select a document
to open its newest version and version history, then select an older version to
inspect its original text. History pagination leaves the displayed version in place.
Direct browsing has no citation highlight or chunk attribution; Q&A retains verified
citation highlighting. **Source details** still exposes immutable IDs, hash and timestamps.

**Filter by title** searches all source titles in the selected workspace, using a
case-insensitive literal substring. Submit **Apply filter** or press Enter; `%` and
`_` are literal characters. **Clear** removes the filter. **Refresh** retains the
applied filter and returns to page one. Catalogue and history pages contain up to
20 items. Filtering, changing catalogue pages or refreshing clears open details.

Switching between **Ask** and **Browse sources** cancels pending requests and clears
open source/browsing state; completed Q&A remains available in the same workspace.
Changing workspace clears both experiences and title drafts. Browsing uses the same
memory-only credentials, access-loss clearing and inert-text rendering as Q&A.
Transient failures expose **Retry**; access failures refresh workspace discovery.

Freshness is a snapshot at read time. There is no polling or stable pagination
snapshot during concurrent uploads; use Refresh to discover new documents/versions.
Uploads and source updates remain existing API operations. No document text is
included in catalogue/history responses; only exact-version reads return full text.
See [Task 006 verification and limitations](docs/TASK_006.md).

### Web development and host serving

Use Node 24+ and npm; Node 22.13+ on the 22.x line is also supported.
Docker builds use Node 24. From the repository root:

```sh
npm --prefix apps/web ci
npm --prefix apps/web run dev
```

Vite binds to `127.0.0.1:5173` and proxies `/api` to `http://127.0.0.1:8000` by
default. Run the host API/database as described above. Set `API_PROXY_TARGET` when
starting Vite to use a different local API port. No CORS configuration is needed.

To serve the production UI from a host API instead:

```sh
npm --prefix apps/web run build
WEB_DIST_DIR=apps/web/dist uv run uvicorn pmknowledge.main:app \
  --host 127.0.0.1 --no-access-log
```

`WEB_DIST_DIR` is optional outside Docker. Unset means API-only mode; a configured
path must contain built `index.html` and `assets/`, or startup fails clearly. The
Docker runtime sets it to `/app/web`, runs as UID 10001 and contains no Node runtime.
Only `/` and `/assets` serve the UI; `/docs`, `/health` and API 404s remain intact.
Authenticated API responses, including failures, use `Cache-Control: no-store`.

### Web verification

```sh
npm --prefix apps/web run typecheck
npm --prefix apps/web run lint
npm --prefix apps/web run format:check
npm --prefix apps/web test
npm --prefix apps/web run build
npm --prefix apps/web exec -- playwright install chromium
```

For real-browser integration, use a dedicated Compose project and unused ports:

```sh
POSTGRES_PASSWORD=localdev POSTGRES_PORT=55436 API_PORT=58006 EMBEDDINGS_ENABLED=false \
  docker compose -p canberra-task006 -f compose.yaml \
  -f apps/web/e2e/compose.yaml up -d --build --wait

E2E_DATABASE_URL=postgresql+psycopg://pmknowledge:localdev@localhost:55436/pmknowledge_test \
E2E_BASE_URL=http://127.0.0.1:58006 \
  npm --prefix apps/web run test:e2e
```

The override runs the API against `pmknowledge_test`. Tests use `uv` and trusted
database credentials to provision synthetic users/workspaces, exercise real HTTP,
then remove only those fixtures. `E2E_DATABASE_URL` is mandatory and must name a
PostgreSQL database ending in `_test`; never point it at a production database.
Browser tests expect embeddings to be disabled. Traces, videos and automatic
screenshots are disabled to avoid recording credentials/source content. An optional
`E2E_SCREENSHOT_PATH` captures only the synthetic evidence walkthrough after connecting.
`E2E_SOURCE_BROWSER_SCREENSHOT_PATH` similarly captures the synthetic source-browser
walkthrough. Save screenshots under `.context/`.

Run the Python checks against the same dedicated database, separately from browser tests:

```sh
TEST_DATABASE_URL=postgresql+psycopg://pmknowledge:localdev@localhost:55436/pmknowledge_test \
  uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mypy apps/api/src
```

When finished, use the same Compose files/project with `down` to stop this slice;
omit `--volumes` to preserve its data. See [Task 005 verification](docs/TASK_005.md)
for recorded results and security limitations. The npm lock includes a scoped
`minimatch` 11 override for the TypeScript lint parser to avoid a vulnerable
transitive range; linting/build/test compatibility is verified with that override.

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
| `GET /api/v1/workspaces/{workspace_id}/sources` | Member token; optional `title`, `limit`, `offset` | `200 {sources, has_more}`; metadata and latest-version identifiers |
| `GET /api/v1/workspaces/{workspace_id}/sources/{source_id}/versions` | Member token; `limit`, `offset` | `200 {versions, has_more}`; version metadata only |
| `POST /api/v1/workspaces/{workspace_id}/sources/{source_id}/versions` | Multipart `file` | `201` new version or `200` existing identical version |
| `GET /api/v1/workspaces/{workspace_id}/sources/{source_id}/versions/{version_id}` | Member token; exact source/version IDs | `200` original text, provenance and computed freshness; historical versions allowed |
| `GET /api/v1/workspaces/{workspace_id}/search` | Query `q`, optional `limit` (default 5, range 1–20), `mode` | `200 {results:[...]}` ranked excerpts |
| `POST /api/v1/workspaces/{workspace_id}/ask` | JSON `{question, limit?, mode?}` | `200 {answer, status, sources}`; at most three quoted citations |
| `POST /api/v1/workspaces/{workspace_id}/sources/{source_id}/versions/{version_id}/proposals` | Editor/owner token; specified latest version | `200 {proposals, created_count}` |
| `GET /api/v1/workspaces/{workspace_id}/proposals` | Editor/owner token; `status`, `limit`, `offset` | `200 {proposals}`; default pending |
| `GET /api/v1/workspaces/{workspace_id}/proposals/{proposal_id}` | Editor/owner token | `200` proposal, evidence and review |
| `POST /api/v1/workspaces/{workspace_id}/proposals/{proposal_id}/review` | Owner token; JSON `{action: "approve" or "reject", comment?}` | `200` updated proposal with nullable `decision_id` |
| `GET /api/v1/workspaces/{workspace_id}/decisions` | Member token; `limit`, `offset` | `200 {decisions}`; approved records only |
| `GET /api/v1/workspaces/{workspace_id}/decisions/{decision_id}` | Member token | `200` decision, evidence, approval attribution and freshness |

Catalogue responses contain `sources` and `has_more`. Source summaries contain
`workspace_id`, `source_document_id`, `title`, nullable `external_uri`, `created_at`,
`latest_version_id`, `latest_version_number` and `latest_ingested_at`. History
responses contain `versions` and `has_more`; rows contain workspace/source/version
UUIDs, `version_number`, `sha256`, `ingested_at` and `source_is_latest`. Both accept
`limit` (default 50, range 1–100) and nonnegative `offset`. Sources sort by creation
timestamp descending then UUID ascending; history sorts by version number descending.
Optional `title` is trimmed, limited to 200 characters and rejects NUL; blank means
unfiltered. Literal matching escapes SQL wildcard and escape characters.

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

## Task 004: extract and review decisions

Extraction is explicit, deterministic and offline. The `decision-marker-v1` rule
selects complete chunks beginning with `Decision:`, `We decided`, `We prioritised`
or `We prioritized` (case-insensitive), with nonblank following content. An optional
Markdown heading prefix is ignored for matching only. Quotes, Unicode and line endings
remain unchanged. Ordinary prose and headings without content produce no proposal.
Source instructions are data and never trigger actions.

With the owner token and workspace from the earlier example, upload the synthetic
decision fixture and extract its proposals:

```sh
DECISION_RECEIPT=$(curl --fail --silent --show-error \
  "http://localhost:8000/api/v1/workspaces/$WORKSPACE_ID/sources" \
  -H "Authorization: Bearer $PMKW_API_TOKEN" \
  -F 'title=First observability release (synthetic)' \
  -F 'file=@apps/api/tests/fixtures/observability-decision.txt')
DECISION_SOURCE_ID=$(printf '%s' "$DECISION_RECEIPT" | jq -er .source_document_id)
DECISION_VERSION_ID=$(printf '%s' "$DECISION_RECEIPT" | jq -er .document_version_id)

PROPOSAL_RECEIPT=$(curl --fail --silent --show-error -X POST \
  "http://localhost:8000/api/v1/workspaces/$WORKSPACE_ID/sources/$DECISION_SOURCE_ID/versions/$DECISION_VERSION_ID/proposals" \
  -H "Authorization: Bearer $PMKW_API_TOKEN")
PROPOSAL_ID=$(printf '%s' "$PROPOSAL_RECEIPT" | jq -er '.proposals[0].id')

# Inspect the exact quotation and its source/version/chunk citation before reviewing.
curl --fail --silent --show-error \
  "http://localhost:8000/api/v1/workspaces/$WORKSPACE_ID/proposals/$PROPOSAL_ID" \
  -H "Authorization: Bearer $PMKW_API_TOKEN" | jq

# An explicit owner action publishes this quotation; use action=reject to reject it.
curl --fail --silent --show-error \
  "http://localhost:8000/api/v1/workspaces/$WORKSPACE_ID/proposals/$PROPOSAL_ID/review" \
  -H "Authorization: Bearer $PMKW_API_TOKEN" -H 'Content-Type: application/json' \
  -d '{"action":"approve","comment":"Reviewed against the synthetic source."}' | jq

curl --fail --silent --show-error \
  "http://localhost:8000/api/v1/workspaces/$WORKSPACE_ID/decisions" \
  -H "Authorization: Bearer $PMKW_API_TOKEN" | jq
```

Proposals include `kind=decision`, `extraction_method=deterministic_source_quotation`,
`extractor_version`, original proposer/time, `status`, `statement`, an `evidence` object
using the existing Evidence fields, nullable `review`, and nullable `decision_id`.
Review includes its UUID, `reviewer_id`, `action`, optional `comment` and `created_at`.
Decisions include a stable UUID, `workspace_id`, `proposal_id`, `statement`, `evidence`,
`approved_by`, `approved_at` and `source_is_latest`. Approval records review judgment;
it establishes neither source truth nor a new interpretation.

Proposal and decision lists order by creation time then UUID and accept `limit`
(default 50, range 1–100) and `offset` (default 0, nonnegative). Proposal `status`
accepts `pending` (default), `approved`, `rejected` or `all`. Extraction results follow
chunk order. No matching marker returns `proposals=[]` and `created_count=0`.
Repeating extraction on the same current version preserves IDs, original proposer
and terminal statuses. Owners may explicitly review proposals they generated.

Review accepts only `action` and optional `comment`; a supplied non-null comment is
trimmed, must be nonblank/NUL-free, and may contain at most 1,000 characters.
Reviewer identity and timestamps come from the server. Approval and publication
commit atomically. Repeating the same action returns the original review without
changing its comment or actor; an opposite action returns `409`.

A newer source version makes extraction from the old version and approval of its
pending proposals return `409`. Rejection remains possible. Prior approvals and their
citations remain readable with `source_is_latest=false`; same-action review retries
still succeed. No automatic withdrawal or supersession occurs. Source/decision text,
proposals and review history have no edit/delete endpoints. Search and ask continue
to quote original sources independently of proposal approval.

This is conservative marker detection, not general decision extraction: it misses
implicit wording and can nominate negated, hypothetical or malicious statements.
It quotes whole existing chunks (up to 1,000 characters), so a long decision may be
split and only its opening chunk selected. Owners must inspect evidence before
approval. Separate chunks, sources and source versions are not semantically deduplicated.
Generation is synchronous and returns all matches within the existing 1 MiB upload
limit; production-scale batching and rate limits remain deferred.

See [Task 004 verification and limitations](docs/TASK_004.md).

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

No external model API, connector, agent orchestration, or external write
action is implemented. Retrieval does not detect contradictions or evaluate whether
an excerpt supports an interpretation. The local embedding model is English-only
and truncates model inputs at 512 tokens; character-based chunks are not token-aware.
The model name and Python dependencies are fixed for this slice; stronger weight
revision pinning and representative threshold calibration remain future work.
Task 003 implementation details and verification are in [Task 003](docs/TASK_003.md).
