# Capabilities and end-to-end testing

Coverage: Tasks 001–011. All supplied content is synthetic.

This document is the single inventory of what PM Knowledge Worker currently does and
how to verify it end to end. [README.md](../README.md) remains canonical for per-task
setup detail and security limitations; if the two disagree, README wins and this
document must be corrected.

## Purpose and scope

- Applies to the implementation through Tasks 001–011.
- Lists user-visible capabilities, their API endpoints, minimum workspace role and
  key source files.
- Provides a repeatable local runbook: Docker Compose quickstart, identity/workspace
  provisioning, a browser walkthrough, a curl smoke test, and automated checks.
- Does not replace the task specifications in `tasks/NNN-*.md` or the verification
  notes in `docs/TASK_NNN.md`.
- Every `/api/v1` endpoint requires `Authorization: Bearer <token>`. `GET /health`,
  `/docs` and the OpenAPI schema are public.

## Capability inventory

Each row names the endpoint template literally as `` `METHOD /api/v1/path` `` with
`{param}` placeholders. Query strings are omitted. This convention is enforced by
`apps/api/tests/test_documentation.py`.

| Area | Capability | Endpoints | Minimum role | Key files |
| --- | --- | --- | --- | --- |
| Identity and workspaces | Resolve the current user; list joined workspaces with role; create a workspace (caller becomes its first owner) | `GET /api/v1/me`<br>`GET /api/v1/workspaces`<br>`POST /api/v1/workspaces` | Any authenticated user | `apps/api/src/pmknowledge/auth.py`, `apps/api/src/pmknowledge/access.py`, `apps/api/src/pmknowledge/main.py` |
| Memberships | List members; create/update a membership; remove a membership. The last owner cannot be removed or demoted | `GET /api/v1/workspaces/{workspace_id}/members`<br>`PUT /api/v1/workspaces/{workspace_id}/members/{user_id}`<br>`DELETE /api/v1/workspaces/{workspace_id}/members/{user_id}` | owner | `apps/api/src/pmknowledge/access.py` |
| Ingestion and provenance | Upload a new Markdown/text source; append an immutable version; deduplicate identical bytes; list sources with title filter; list versions; read an exact version's original text, SHA-256, offsets and computed freshness | `POST /api/v1/workspaces/{workspace_id}/sources`<br>`GET /api/v1/workspaces/{workspace_id}/sources`<br>`POST /api/v1/workspaces/{workspace_id}/sources/{source_id}/versions`<br>`GET /api/v1/workspaces/{workspace_id}/sources/{source_id}/versions`<br>`GET /api/v1/workspaces/{workspace_id}/sources/{source_id}/versions/{version_id}` | reader for reads; editor for uploads | `apps/api/src/pmknowledge/documents.py`, `apps/api/src/pmknowledge/chunking.py`, `apps/api/src/pmknowledge/models.py`, `apps/api/migrations/versions/0001_knowledge_foundation.py` |
| Search and Q&A | Keyword, semantic or hybrid retrieval (workspace-filtered before ranking); conservative lexical/cosine selection, exact-text deduplication and at most three complete quoted chunks, or `insufficient_evidence`. Search ranking is unchanged | `GET /api/v1/workspaces/{workspace_id}/search`<br>`POST /api/v1/workspaces/{workspace_id}/ask` | reader | `apps/api/src/pmknowledge/retrieval.py`, `apps/api/src/pmknowledge/answer_selection.py`, `apps/api/src/pmknowledge/embeddings.py` |
| Decisions | Generate deterministic `decision-marker-v1` proposals from a latest version; browse the queue; inspect a proposal; approve/reject as owner; browse and read immutable approved decisions | `POST /api/v1/workspaces/{workspace_id}/sources/{source_id}/versions/{version_id}/proposals`<br>`GET /api/v1/workspaces/{workspace_id}/proposals`<br>`GET /api/v1/workspaces/{workspace_id}/proposals/{proposal_id}`<br>`POST /api/v1/workspaces/{workspace_id}/proposals/{proposal_id}/review`<br>`GET /api/v1/workspaces/{workspace_id}/decisions`<br>`GET /api/v1/workspaces/{workspace_id}/decisions/{decision_id}` | editor for proposals; owner for review; reader for decisions | `apps/api/src/pmknowledge/decisions.py`, `apps/api/migrations/versions/0004_decision_review.py` |
| Feedback | Submit explicit Helpful/Not helpful feedback with optional reason and comment (idempotent by `submission_id`); owner-only list by rating and detail with saved Q&A context | `POST /api/v1/workspaces/{workspace_id}/feedback`<br>`GET /api/v1/workspaces/{workspace_id}/feedback`<br>`GET /api/v1/workspaces/{workspace_id}/feedback/{feedback_id}` | reader to submit; owner to inspect | `apps/api/src/pmknowledge/feedback.py`, `apps/api/migrations/versions/0005_answer_feedback.py` |
| Web and operations | React SPA at `/` and `/assets`; public `GET /health` and `/docs`; structured request logs; explicit Alembic migrations; optional local CPU embeddings | No `/api/v1` routes | n/a | `apps/web/src/App.tsx`, `apps/web/src/useKnowledge.ts`, `apps/api/src/pmknowledge/main.py`, `compose.yaml`, `alembic.ini` |
| Pilot evaluation | Offline synthetic retrieval/answer benchmark; explicit modes and answer policy, paired first-three/selected answers on identical candidates, span relevance, independent citation checks, workspace/version probes, bounded development calibration and held-out release gates; rollback-only fixtures | No HTTP endpoints; operator CLI | Database operator | `apps/api/src/pmknowledge/evaluation.py`, `apps/api/src/pmknowledge/evaluation_checks.py`, `apps/api/src/pmknowledge/selection_benchmark.py` |

## Roles and permissions

Workspace roles are hierarchical: `reader` < `editor` < `owner` (`access.py`).

| Capability | reader | editor | owner |
| --- | --- | --- | --- |
| Search, ask, browse sources/versions, read exact versions | yes | yes | yes |
| Read approved decisions | yes | yes | yes |
| Submit feedback | yes | yes | yes |
| Upload sources and new versions | no | yes | yes |
| Generate, list and inspect proposals | no | yes | yes |
| Approve or reject proposals | no | no | yes |
| Inspect feedback | no | no | yes |
| Manage memberships | no | no | yes |

- Requests outside the workspace still return `404`, so non-members cannot probe IDs.
- A member with an insufficient role receives `403`.
- The last owner cannot be removed or demoted, including under concurrent requests.
- In the SPA, the Feedback view is owner-only; Review queue appears for editor and
  owner; upload controls appear for editor and owner.

## What is not built

- No signup endpoint, password login, SSO, or token-management UI. Operators provision
  identities with the CLI.
- No UI for creating users, tokens, workspaces or memberships. The SPA lists only
  joined workspaces and shows "No workspaces yet" otherwise.
- No per-document ACLs: every source and embedding in a workspace shares its boundary.
- No LLM or abstractive answer generation. `/ask` returns verbatim quotations only.
  The only model is the opt-in local embedding model.
- No source, version, decision or feedback editing/deletion; no retention, export,
  resolution workflow or feedback analytics.
- No external connectors, reindexing, change detection, or external write actions.
- No rate limiting, TLS termination, backup/encryption setup or production deployment
  configuration.
- No CI configuration; the checks in this document run locally.

See [README security limitations](../README.md#security-limitations).

## Run the stack locally

### Docker Compose (recommended)

Requires Docker with Compose v2+; run from the repository root.

```sh
# First run only; keep an existing .env if you have already configured one.
cp .env.example .env
docker compose up -d --build --wait
curl --fail http://localhost:8000/health
```

- Web UI: <http://localhost:8000>
- API contract: <http://localhost:8000/docs>
- Compose waits for PostgreSQL and runs `alembic upgrade head` before starting the API.
- Services bind to `127.0.0.1`. `POSTGRES_PASSWORD` must be non-empty.
- `docker compose down` preserves the data volume; omit `--volumes` to keep data.

### Host API with the Compose database

```sh
uv python install 3.12
uv sync --dev --frozen
docker compose up -d --wait db
uv run alembic upgrade head
uv run uvicorn pmknowledge.main:app --reload --host 127.0.0.1 --no-access-log
```

Stop the container API first (`docker compose stop api`) if it holds port 8000.
Application startup never creates schema implicitly.

### Web development server (optional)

```sh
npm --prefix apps/web ci
npm --prefix apps/web run dev
```

Vite serves <http://127.0.0.1:5173> and proxies `/api` to `http://127.0.0.1:8000`.
Set `API_PROXY_TARGET` to proxy elsewhere. To serve a production build from the host
API instead:

```sh
npm --prefix apps/web run build
WEB_DIST_DIR=apps/web/dist uv run uvicorn pmknowledge.main:app \
  --host 127.0.0.1 --no-access-log
```

## Provision an identity and workspace

There is no default credential. Capture the operator outputs in one shell session.

### Create a user and token (operator CLI)

Requires `jq`. With Compose:

```sh
PMKW_USER_ID=$(docker compose exec -T api uv run --no-sync python -m pmknowledge.auth \
  create-user --name 'Synthetic Aurora member' | jq -er .id)
PMKW_TOKEN_RECEIPT=$(docker compose exec -T api uv run --no-sync python -m pmknowledge.auth \
  issue-token --user-id "$PMKW_USER_ID")
PMKW_API_TOKEN=$(printf '%s' "$PMKW_TOKEN_RECEIPT" | jq -er .token)
export PMKW_API_TOKEN
```

Plaintext is returned only at issuance; the database stores a SHA-256 digest. Tokens
expire after 30 days by default. Revoke with
`python -m pmknowledge.auth revoke-token --token-id TOKEN_UUID`.

On the host API path, run the same commands without the `docker compose exec -T api`
prefix and without `--no-sync`.

### Create a workspace (API or curl)

The web UI cannot create workspaces. Use the API:

```sh
WORKSPACE_ID=$(curl --fail --silent --show-error http://localhost:8000/api/v1/workspaces \
  -H "Authorization: Bearer $PMKW_API_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Synthetic Aurora team"}' | jq -er .id)
echo "$WORKSPACE_ID"
```

The creator becomes owner atomically. Alternatively use **Authorize** in `/docs`,
then `POST /api/v1/workspaces` with body `{"name": "Synthetic Aurora team"}`.
Workspace names are trimmed, 1–200 characters, and must not contain NUL.

After creation, reload the SPA, or click **Disconnect** and **Connect** again, so the
workspace list refreshes.

For a workspace created before membership existed, an operator can assign the owner:

```sh
docker compose exec -T api uv run --no-sync python -m pmknowledge.auth \
  grant-owner --workspace-id "$WORKSPACE_ID" --user-id "$PMKW_USER_ID"
```

### Manage memberships

Owners can list, upsert and remove members:

```sh
curl --silent --show-error "http://localhost:8000/api/v1/workspaces/$WORKSPACE_ID/members" \
  -H "Authorization: Bearer $PMKW_API_TOKEN" | jq

curl --fail --silent --show-error -X PUT \
  "http://localhost:8000/api/v1/workspaces/$WORKSPACE_ID/members/$READER_USER_ID" \
  -H "Authorization: Bearer $PMKW_API_TOKEN" \
  -H 'Content-Type: application/json' -d '{"role":"reader"}' | jq
```

Roles are `reader`, `editor` and `owner`. The last owner cannot be removed or demoted.

## Browser walkthrough

1. Open <http://localhost:8000>, paste the bearer token and click **Connect**. The
   first joined workspace is selected automatically.
2. **Ask** is the default view. In keyword mode ask:
   *Why was troubleshooting acceleration prioritised in the first observability
   release?* Expect `Extracted evidence (verbatim source text)` with numbered
   citations. Click a citation to inspect the exact source version, the verified
   highlighted character span, and **Source details** (IDs, offsets, hash, ingestion
   time, inert URI). A **Historical version** label means newer content exists.
3. Ask `nonexistentplatypus`; expect `insufficient_evidence` and no sources.
4. **Browse sources**: filter by title, page through results, open version history and
   read original text.
5. **Upload** (editor/owner): create a source from a `.md`, `.markdown` or `.txt` file
   (UTF-8, ≤1 MiB). Uploading an identical file again reports a duplicate rather than
   creating a version. Upload changed bytes to append a new version.
6. **Decisions**: generate proposals from a decision-bearing source's latest version
   (editor/owner). **Review queue** lists pending proposals for editor/owner; only an
   owner can approve or reject. Approval publishes one immutable decision.
7. **Feedback**: after an answer, submit Helpful or Not helpful with an optional
   reason/comment. Owners see the **Feedback** view with rating filter and saved Q&A
   context.
8. **Roles**: a reader sees no Review queue, no upload controls and no Feedback view.
   An editor can upload and generate proposals but cannot approve them.
9. Session state: tokens, questions and answers live in tab memory. Reload or
   **Disconnect** clears them; only explicitly submitted feedback is persisted
   server-side. Revoked credentials require reconnecting.

## Curl smoke test

Requires a running stack plus `jq` and `uuidgen`. Run from the repository root after
provisioning `PMKW_API_TOKEN` and `WORKSPACE_ID` above. The membership step's
`docker compose exec` calls assume the Compose quickstart; on the host path run the
same `uv run python -m pmknowledge.auth` commands directly.

```sh
set -euo pipefail
API=http://localhost:8000
AUTH="Authorization: Bearer $PMKW_API_TOKEN"

# Identity and workspace discovery.
curl -sS "$API/api/v1/me" -H "$AUTH" | jq
curl -sS "$API/api/v1/workspaces" -H "$AUTH" | jq

# Upload both synthetic fixtures; capture IDs from the ingestion receipts.
STRATEGY=$(curl -sS --fail "$API/api/v1/workspaces/$WORKSPACE_ID/sources" -H "$AUTH" \
  -F 'title=Observability strategy (synthetic)' \
  -F 'external_uri=https://example.invalid/observability-strategy' \
  -F 'file=@apps/api/tests/fixtures/observability-strategy.md')
SOURCE_ID=$(printf '%s' "$STRATEGY" | jq -er .source_document_id)
STRATEGY_VERSION_ID=$(printf '%s' "$STRATEGY" | jq -er .document_version_id)

DECISION=$(curl -sS --fail "$API/api/v1/workspaces/$WORKSPACE_ID/sources" -H "$AUTH" \
  -F 'title=First release decision (synthetic)' \
  -F 'file=@apps/api/tests/fixtures/observability-decision.txt')
DECISION_SOURCE_ID=$(printf '%s' "$DECISION" | jq -er .source_document_id)
DECISION_VERSION_ID=$(printf '%s' "$DECISION" | jq -er .document_version_id)

# Browser-equivalent reads: title filter, versions, exact version text.
curl -sS -G "$API/api/v1/workspaces/$WORKSPACE_ID/sources" -H "$AUTH" \
  --data-urlencode 'title=Observability' | jq
curl -sS "$API/api/v1/workspaces/$WORKSPACE_ID/sources/$SOURCE_ID/versions" -H "$AUTH" | jq
curl -sS "$API/api/v1/workspaces/$WORKSPACE_ID/sources/$SOURCE_ID/versions/$STRATEGY_VERSION_ID" \
  -H "$AUTH" | jq '{version_number, source_is_latest, sha256, plain_text}'

# Identical bytes: HTTP 200 with duplicate=true and unchanged IDs.
curl -sS -o /dev/null -w 'duplicate upload status=%{http_code}\n' \
  "$API/api/v1/workspaces/$WORKSPACE_ID/sources/$SOURCE_ID/versions" -H "$AUTH" \
  -F 'file=@apps/api/tests/fixtures/observability-strategy.md'
curl -sS "$API/api/v1/workspaces/$WORKSPACE_ID/sources/$SOURCE_ID/versions" -H "$AUTH" \
  -F 'file=@apps/api/tests/fixtures/observability-strategy.md' \
  | jq '{duplicate, version_number, document_version_id}'

# Keyword search and a grounded answer with citations.
curl -sS -G "$API/api/v1/workspaces/$WORKSPACE_ID/search" -H "$AUTH" \
  --data-urlencode 'q=troubleshooting acceleration' --data-urlencode 'mode=keyword' | jq
ASK_RESPONSE=$(curl -sS --fail "$API/api/v1/workspaces/$WORKSPACE_ID/ask" -H "$AUTH" \
  -H 'Content-Type: application/json' \
  -d '{"question":"Why was troubleshooting acceleration prioritised in the first observability release?","mode":"keyword"}')
printf '%s' "$ASK_RESPONSE" | jq '{status, answer, citations: [.sources[].citation]}'

# No matching terms: status=insufficient_evidence and sources=[].
curl -sS --fail "$API/api/v1/workspaces/$WORKSPACE_ID/ask" -H "$AUTH" \
  -H 'Content-Type: application/json' -d '{"question":"nonexistentplatypus"}' \
  | jq '{status, sources}'

# Generate proposals from the latest decision source version, then inspect the queue.
PROPOSALS=$(curl -sS --fail -X POST \
  "$API/api/v1/workspaces/$WORKSPACE_ID/sources/$DECISION_SOURCE_ID/versions/$DECISION_VERSION_ID/proposals" \
  -H "$AUTH")
printf '%s' "$PROPOSALS" | jq '{created_count, proposals: [.proposals[] | {id, status, statement}]}'
PROPOSAL_ID=$(printf '%s' "$PROPOSALS" | jq -er '.proposals[0].id')
curl -sS "$API/api/v1/workspaces/$WORKSPACE_ID/proposals?status=all" -H "$AUTH" | jq
curl -sS "$API/api/v1/workspaces/$WORKSPACE_ID/proposals/$PROPOSAL_ID" -H "$AUTH" | jq

# Owner approval publishes one immutable decision.
REVIEW=$(curl -sS --fail -X POST \
  "$API/api/v1/workspaces/$WORKSPACE_ID/proposals/$PROPOSAL_ID/review" -H "$AUTH" \
  -H 'Content-Type: application/json' \
  -d '{"action":"approve","comment":"Synthetic smoke-test approval"}')
printf '%s' "$REVIEW" | jq '{status, decision_id}'
DECISION_ID=$(printf '%s' "$REVIEW" | jq -er .decision_id)
curl -sS "$API/api/v1/workspaces/$WORKSPACE_ID/decisions" -H "$AUTH" | jq
curl -sS "$API/api/v1/workspaces/$WORKSPACE_ID/decisions/$DECISION_ID" -H "$AUTH" | jq

# Submit feedback built from the saved answer; replay is idempotent (201 then 200).
FEEDBACK_PAYLOAD=$(jq -n \
  --arg submission_id "$(uuidgen | tr '[:upper:]' '[:lower:]')" \
  --argjson answer "$(printf '%s' "$ASK_RESPONSE" | jq -c '{answer, status, sources}')" \
  '{submission_id: $submission_id,
    question: "Why was troubleshooting acceleration prioritised in the first observability release?",
    mode: "keyword", answer: $answer, rating: "not_helpful",
    reason: "missing_evidence", comment: "Synthetic smoke-test feedback"}')
curl -sS -o /dev/null -w 'first feedback status=%{http_code}\n' -X POST \
  "$API/api/v1/workspaces/$WORKSPACE_ID/feedback" -H "$AUTH" \
  -H 'Content-Type: application/json' -d "$FEEDBACK_PAYLOAD"
curl -sS -o /dev/null -w 'replayed feedback status=%{http_code}\n' -X POST \
  "$API/api/v1/workspaces/$WORKSPACE_ID/feedback" -H "$AUTH" \
  -H 'Content-Type: application/json' -d "$FEEDBACK_PAYLOAD"
FEEDBACK_ID=$(curl -sS "$API/api/v1/workspaces/$WORKSPACE_ID/feedback" -H "$AUTH" \
  | jq -er '.feedback[0].id')
curl -sS "$API/api/v1/workspaces/$WORKSPACE_ID/feedback/$FEEDBACK_ID" -H "$AUTH" | jq

# Membership flow: add a reader, confirm upload is forbidden, then remove the reader.
READER_USER_ID=$(docker compose exec -T api uv run --no-sync python -m pmknowledge.auth \
  create-user --name 'Synthetic reader' | jq -er .id)
READER_TOKEN=$(docker compose exec -T api uv run --no-sync python -m pmknowledge.auth \
  issue-token --user-id "$READER_USER_ID" | jq -er .token)
curl -sS -X PUT "$API/api/v1/workspaces/$WORKSPACE_ID/members/$READER_USER_ID" -H "$AUTH" \
  -H 'Content-Type: application/json' -d '{"role":"reader"}' | jq
curl -sS "$API/api/v1/workspaces/$WORKSPACE_ID/members" -H "$AUTH" | jq
curl -sS -o /dev/null -w 'reader upload status=%{http_code}\n' -X POST \
  "$API/api/v1/workspaces/$WORKSPACE_ID/sources" \
  -H "Authorization: Bearer $READER_TOKEN" -F 'title=Denied' \
  -F 'file=@apps/api/tests/fixtures/observability-strategy.md'
curl -sS -o /dev/null -w 'delete member status=%{http_code}\n' -X DELETE \
  "$API/api/v1/workspaces/$WORKSPACE_ID/members/$READER_USER_ID" -H "$AUTH"

curl -sS --fail "$API/health" | jq
```

Expected signals: the grounded answer is labelled
`Extracted evidence (verbatim source text)` and contains the synthetic quote about
troubleshooting acceleration; the unrelated question returns `insufficient_evidence`;
the duplicate version returns HTTP 200 with `duplicate=true`; feedback returns 201 then
200; the reader upload returns 403; member deletion returns 204.

## Automated tests and checks

The backend suite requires PostgreSQL. The database container creates both
`pmknowledge` and `pmknowledge_test` on first initialization, and pytest runs Alembic
against the test database automatically.

| Area | Test modules |
| --- | --- |
| Auth and access | `test_auth.py`, `test_access.py`, `test_access_migration.py` |
| Ingestion, chunking, versions | `test_api.py`, `test_chunking.py`, `test_source_reads.py`, `test_source_browsing.py` |
| Retrieval and evaluation | `test_semantic.py`, `test_fusion.py`, `test_evaluation.py`, `test_pilot_evaluation.py` |
| Answer selection and release gates | `test_answer_selection.py`, `test_selection_benchmark.py` |
| Decisions | `test_decisions.py`, `test_decision_extraction.py`, `test_decision_concurrency.py`, `test_decision_migration.py` |
| Feedback | `test_feedback.py`, `test_feedback_migration.py` |
| Web serving and health | `test_web.py`, `test_health.py` |
| Documentation guard | `test_documentation.py` |

Backend:

```sh
uv sync --dev --frozen
docker compose up -d --wait db
uv run pytest                                  # full suite (PostgreSQL required)
uv run pytest -m 'not integration'             # database-free subset
uv run ruff check .
uv run ruff format --check .
uv run mypy apps/api/src
uv run alembic check
```

`TEST_DATABASE_URL` overrides the test database and must name a PostgreSQL database
ending in `_test`; the full suite fails if PostgreSQL is unavailable rather than
silently skipping. `alembic check` expects the development database to be migrated
first (`uv run alembic upgrade head`). See
[README tests and checks](../README.md#tests-and-checks).

Web unit and static checks:

```sh
npm --prefix apps/web ci
npm --prefix apps/web run typecheck
npm --prefix apps/web run lint
npm --prefix apps/web run format:check
npm --prefix apps/web test
npm --prefix apps/web run build
```

Browser E2E (Playwright, Chromium). Use a dedicated Compose project so the API runs
against the test database:

```sh
npm --prefix apps/web exec -- playwright install chromium

POSTGRES_PASSWORD=localdev POSTGRES_PORT=55439 API_PORT=58009 EMBEDDINGS_ENABLED=false \
  docker compose -p pmkw-e2e -f compose.yaml -f apps/web/e2e/compose.yaml up -d --build --wait

E2E_DATABASE_URL=postgresql+psycopg://pmknowledge:localdev@localhost:55439/pmknowledge_test \
E2E_BASE_URL=http://127.0.0.1:58009 \
  npm --prefix apps/web run test:e2e
```

`E2E_DATABASE_URL` is mandatory and must end in `_test`; never point it at production.
The suite provisions and removes only synthetic users/workspaces. Optional
`E2E_*_SCREENSHOT_PATH` variables capture the synthetic walkthroughs; save them under
`.context/`.

## Optional semantic and hybrid mode

Task 010's [pilot evaluation runbook](../README.md#task-010-pilot-evaluation-baseline)
uses 20 synthetic documents and 40 labelled questions. Keyword-only benchmarking
requires no model; the recorded baseline includes all three modes using cached weights.
See [results and limitations](TASK_010.md). Quality metrics do not gate success;
evidence-integrity and isolation checks do. This is an operator CLI, not a member API.

Keyword retrieval is the default and needs no model. Semantic and hybrid modes need
the opt-in local CPU embedding model (`BAAI/bge-small-en-v1.5`, 384 dimensions):

```sh
docker compose run --rm --no-deps -e HF_HUB_OFFLINE=0 api \
  uv run --no-sync python -m pmknowledge.embeddings download

# Set EMBEDDINGS_ENABLED=true in .env, then:
docker compose up -d --wait api

# Embed sources uploaded before embeddings were enabled:
docker compose exec -T api uv run --no-sync python -m pmknowledge.embeddings \
  backfill --workspace-id "$WORKSPACE_ID"
```

Then pass `mode=semantic` or `mode=hybrid` to search/ask. When embeddings are
disabled or weights are missing, these modes return `503` with a clear message; there
is no silent fallback to keyword. Semantic mode is English-only and truncates chunks
at 512 tokens. See `docs/TASK_002.md` for recorded evaluation results and limits.

Task 011 enables a frozen selector for `/ask` after passing held-out gates at both
candidate budgets. It preserves exact chunks and at most three citations; `limit`
still bounds candidates. Empty English query lexemes produce insufficient evidence.
Keyword selection requires positive overlap (threshold 0); semantic/hybrid can also
qualify with raw cosine at least 0.65 and the configured floor. Lexical thresholds
are 0.30 for semantic and 0.80 for hybrid. Duplicate excerpt strings appear once.
Related quotations may still omit the requested fact; `grounded` is not proof of
answerability. Search, source navigation, feedback formats and roles are unchanged.

Evaluation report version 3 keeps the old search metrics and adds answer abstention,
paired policies and captured selection inputs. `--answer-policy legacy` reproduces
the former answer policy; `selected` matches production. The dedicated operator
calibration/validation commands and fixed artifact paths are documented in
[Task 011 verification](TASK_011.md). A gate failure exits 1 and does not change
production defaults. No script automatically promotes a policy.

## Keeping this document current

This document is part of each task's definition of done. When a change adds, removes
or alters a capability, endpoint, role rule, setup command or test workflow, update the
affected section in the same change.

`apps/api/tests/test_documentation.py` enforces the structural rules:

- every `/api/v1` `METHOD path` operation exposed by the OpenAPI schema must appear in
  the **Capability inventory** as a literal backticked `` `METHOD /api/v1/path` ``;
- documented endpoint operations that no longer exist fail the guard as stale;
- the required H2 sections and title must remain present;
- this path must be linked from `README.md` and `AGENTS.md`;
- `Coverage: Tasks 001–NNN.` must match the highest `tasks/NNN-*.md` file, which
  catches UI-only capability changes that add no endpoint.

Update recipe for a new task:

1. Add or edit capability rows and any prose that changed.
2. Add new endpoints exactly as `` `METHOD /api/v1/path` `` with `{param}` placeholders.
3. Update the `Coverage:` marker.
4. Run `uv run pytest apps/api/tests/test_documentation.py -q`.

The guard reads the OpenAPI schema, so keep implemented `/api/v1` routes
schema-visible. Routes marked `include_in_schema=False` are intentionally not
detected. If task specifications are ever written before their implementation, update
the coverage marker only when the implementation lands.
