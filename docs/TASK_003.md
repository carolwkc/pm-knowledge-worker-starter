# Task 003: authenticated workspace access

Historical verification record: Task 003 subsequently merged as PR #3 before
Task 004 began. The review-boundary notes below describe its original handoff.

## Delivered slice

- Mandatory opaque bearer tokens across `/api/v1`; public health, OpenAPI and docs.
  Credentials are checked against PostgreSQL on every request. Authentication cannot
  be disabled and never falls back when the database is unavailable.
- Local users, unique SHA-256 token digests, expiry/revocation and role-constrained
  workspace memberships through migration `0003`. Tokens contain 32 random bytes,
  expire after 30 days by default and are returned only once, after issuance commits.
- Trusted operator CLI: `create-user`, `issue-token`, `revoke-token`, `grant-owner`.
  Existing workspaces receive no implicit membership; explicit owner assignment is
  repeatable. No source evidence, embeddings or citation IDs are rewritten.
- Current-user and joined-workspace discovery, atomic initial ownership and owner-only
  membership listing/upsert/removal. Readers search/ask; editors also upload/version;
  owners also administer membership. All workspace sources share permissions.
- Identity is explicit at ingestion/search/ask service boundaries. Both SQL retrievers
  require membership and workspace/latest-version predicates before ranking/limits.
  Denied API requests cannot reach document processing or embedding inference.
- Membership mutations serialize on the workspace row and recheck acting ownership
  after waiting. Final-owner removal/demotion returns 409. Token/membership revocation
  and role changes apply to subsequent requests; in-flight requests may finish.
- Backfill remains a trusted database-operator command. Evaluation creates its own
  synthetic identity/membership and rolls them back with its temporary evidence.

Setup and API contracts are in [README](../README.md#task-003-provision-an-identity-and-workspace-access).
The implementation task is [Task 003](../tasks/003-workspace-access.md).

## Verification

Executed with Python 3.12.12, PostgreSQL 16/pgvector and the Linux arm64 API image.
This workspace uses ports **55432** (database) and **58000** (API), because another
workspace already occupied the default ports. Its containers and volumes were left
alone. The local `.env` records this workspace's overrides and is ignored by Git.

| Command / scenario | Recorded outcome |
| --- | --- |
| `uv sync --dev --frozen` | Installed locked dependencies; no dependency changes |
| `TEST_DATABASE_URL=postgresql+psycopg://pmknowledge:localdev@localhost:55432/pmknowledge_test uv run pytest -q` | 93 passed; no skips or warnings |
| `uv run ruff check .` | Passed |
| `uv run ruff format --check .` | Passed |
| `uv run mypy apps/api/src` | Passed, 13 source files |
| `uv run alembic upgrade head` | Passed through `0003` |
| `uv run alembic check` | No new upgrade operations detected |
| Docker Compose build/start with temporary credential-free config | Image built; API and database healthy |
| Docker HTTP smoke | Passed identity, workspace discovery, roles, source-to-answer provenance, duplicate/version handling, missing evidence, last-owner protection and next-request revocation |
| Container logs inspected by the smoke | No issued plaintext credentials present |
| Smoke cleanup | Removed only the users/workspaces created by the smoke |

The initial missing/malformed credential tests were observed failing with 503 instead
of 401; the CLI test failed because the provisioning module did not yet exist. Both
passed after implementation. Existing Task 001–002 regression tests now use real
issued credentials, including custom semantic clients; authentication is not bypassed.

Security tests additionally cover foreign-workspace concealment, forged identity/role
headers, expiry and independent token revocation, every workspace role, membership
removal/demotion, concurrent owner demotions and rechecking an actor after an actual
PostgreSQL lock wait. Controlled-vector tests put more foreign candidates than the
hybrid candidate limit ahead of accessible evidence, verify returned excerpts/citations,
and directly exercise the SQL membership filters. Denied requests use an embedder
that raises if inference is reached. These tests establish permission behavior, not
new claims about semantic retrieval quality.

An isolated-schema migration test starts at `0002` with source/version/chunk/embedding
data, verifies that upgrade preserves the complete evidence snapshot and assigns no
users/tokens/memberships, and verifies source preservation on downgrade. It does not
downgrade the shared test or development schema. Evaluation cleanup tests verify user
and membership counts as well as workspace cleanup.

The first Docker build was cancelled after `docker-credential-desktop` stalled during
public base-image resolution. Both registries were reachable. Using an ignored,
temporary Docker config with empty `auths` resolved image metadata in under one second;
no global Docker setting or credential was changed. The successful build command was:

```sh
DOCKER_CONFIG="$PWD/.context/docker-config" \
DOCKER_HOST=unix:///Users/carol/.docker/run/docker.sock \
docker compose up -d --build --wait
```

The HTTP smoke script and credential-free report are local artifacts under `.context/`.
No real confidential content, external model API or external write action was used.
Final review was an author self-review; independent review remains the next step.

## Limitations and review boundary

- This is local API authentication, not production identity lifecycle or deployment
  hardening. SSO, password login, account recovery, TLS termination, rate limiting,
  retention and production audit/lifecycle controls remain deferred.
- Permissions apply to the whole workspace; there are no per-source ACLs. Owners
  receive access to every source and derived embedding in their workspace.
- Operator CLI/database credentials remain privileged. The final-owner rule is an
  application invariant, not protection against direct privileged SQL or user deletion.
- Multipart parsing can spool request bodies before service-level authorization;
  this task does not add request-stream size enforcement.
- Tokens and membership are checked each request; a committed revocation does not
  cancel an operation already underway. There are no permission/answer caches.
- Original extractive-answer and retrieval-quality limitations still apply. Public
  API documentation exposes schemas, not stored evidence.

Task 003 is ready for review. Review it before starting Task 004.
