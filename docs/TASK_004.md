# Task 004: decision extraction proposals and approval

## Delivered slice

- Alembic migration `0004` adds proposals, terminal review events and approved
  decisions. Existing evidence, source/version/chunk IDs, embeddings, users, tokens
  and memberships are preserved. No proposal is generated during migration/ingestion.
- Editors/owners explicitly extract from a specified latest source version.
  `decision-marker-v1` conservatively selects whole chunks beginning with explicit
  decision markers and preserves original text, offsets and attribution. Duplicate
  generation retains proposal IDs, statuses and the original proposing user.
- Editors/owners inspect proposals; owners approve/reject, including their own.
  Approval atomically stores one terminal review and one decision. Rejection stores
  no decision. Same-action retries retain the original review, actor and comment;
  opposite actions fail with 409. All members can read approved decisions.
- Pending approvals require current source evidence. Source updates block old-version
  extraction/approval but allow rejection. Published decisions retain pinned evidence
  and expose `source_is_latest=false` after a source update. No automatic supersession.
- Six bearer-authenticated endpoints reuse the Evidence shape and workspace access
  conventions. Queue filters and bounded list pagination are documented in README.
  Source search/ask contracts and retrieval behavior are unchanged.
- Task 003 is merged as PR #3; outdated delivery status was corrected. The original
  Task 003 verification report is retained as a historical record.

See the [implementation specification](../tasks/004-decision-review.md) and
[API contracts and synthetic walkthrough](../README.md#task-004-extract-and-review-decisions).

## Verification

Executed on 2026-11-15 using Python 3.12.12 and PostgreSQL 16/pgvector. Tests and
the live smoke use the isolated Compose project **dublin-task004**, database port
**55433**, and temporary host API port **58001**. Other Conductor workspaces,
containers and volumes were left alone. No dependency or lockfile changes were needed.

| Command / scenario | Recorded outcome |
| --- | --- |
| `uv sync --dev --frozen` | Installed locked dependencies |
| Existing baseline suite before implementation | 93 passed |
| `TEST_DATABASE_URL=postgresql+psycopg://pmknowledge:localdev@localhost:55433/pmknowledge_test uv run pytest -q` | **137 passed**, no skips or warnings |
| `uv run ruff check .` | Passed |
| `uv run ruff format --check .` | Passed, 47 files already formatted |
| `uv run mypy apps/api/src` | Passed, 14 source files |
| `DATABASE_URL=postgresql+psycopg://pmknowledge:localdev@localhost:55433/pmknowledge uv run alembic upgrade head` | Passed through `0004` |
| Same URL with `uv run alembic check` | No new upgrade operations detected |
| `uv run python .context/task004_smoke.py` | Passed 15 live HTTP scenarios; temporary server stopped and only smoke-created user/workspace removed |
| `git diff --check` | Passed |

To recreate this isolated database on the verification Mac:

```sh
DOCKER_HOST=unix:///Users/carol/.docker/run/docker.sock \
POSTGRES_PASSWORD=localdev POSTGRES_PORT=55433 API_PORT=58001 \
  docker compose -p dublin-task004 up -d --wait db
```

On another host, omit `DOCKER_HOST` when the default Docker socket works. Use the
URLs in the table to migrate and test; no tracked or ignored `.env` was changed.
The isolated database container remains running for review. The smoke script and
credential-free result/log artifacts are under `.context/`; this directory is local
and ignored, while the README walkthrough and automated tests are repository artifacts.
No Docker API-image rebuild was performed for this task; the live smoke ran Uvicorn
from the locked host environment against the migrated database.

Tests cover exact Unicode/CRLF provenance; ordinary prose/empty marker abstention;
instruction-like source text staying untrusted; generation idempotency; approval,
rejection and terminal retries; freshness; list filters/pagination; real credentials;
all workspace roles; foreign workspace/resource IDs; identity spoofing; revocation;
and invalid review payloads without echoing submitted content in logs/errors.

Actual PostgreSQL lock tests cover concurrent extraction by different users,
competing approvals/rejections, upload-before-approval ordering, owner/editor
demotion while requests wait, and new-version extraction concurrent with review of
an older proposal. A storage-failure injection verifies complete rollback, followed
by a successful retry. Coordinated concurrent GET/list tests verify that a proposal's
status, review and publication always come from the same database snapshot.

An isolated-schema `0003 → 0004 → 0003` test preserves complete snapshots of evidence,
embeddings and access data, and downgrades even with a populated proposal/review/decision.
Shared development/test schemas are never downgraded by these tests.

## Independent review and corrections

A fresh reviewer inspected the implementation read-only and identified two important
concurrency defects. Both were reproduced with failing automated regressions, fixed,
and included in the final 137-test passing suite:

1. **Foreign-key lock inversion:** extracting a new source version while reviewing
   an old proposal could deadlock, returning 503. Generation now acquires the workspace
   key-share lock before the source update lock. This is the one lock-order addition
   to the approved plan: workspace review/membership writers may wait for an active
   extraction, preventing the implicit FK check from reversing their lock order.
2. **Mixed proposal snapshots:** separate reads could return pending status alongside
   an approval event/decision. Proposal, evidence, review and decision now use one
   joined SQL statement, including queue filtering and detail responses.

The independent reviewer did not run tests or perform a second review after the fixes;
the author ran the regression tests and full verification above. No critical or minor
findings were reported. Semantic extraction quality, production scaling, privileged
direct SQL changes and cancellation of requests already underway were deliberately
outside the review scope, consistent with the documented slice.

During the lock-order correction, a test that attempted membership mutation while
holding a source lock was interrupted and updated to exercise the new workspace-lock
boundary. Its three leftover synthetic rows were explicitly cleaned from this task's
isolated test database. The final suite completed normally.

## Limitations

- Marker matching is not semantic reasoning: it can miss implicit decisions or
  nominate hypothetical, negated or malicious text. Human approval does not prove
  factual truth. Content is an exact source quotation, not an inferred interpretation.
- Existing character-based chunks can truncate a long decision; only matching
  opening chunks are nominated. There is no semantic deduplication across sources,
  versions or chunks, no extraction-quality benchmark and no model involved.
- Generation is synchronous and returns all matching chunks within the existing
  1 MiB upload limit. Production batching, rate limits and performance calibration
  are deferred. List APIs are bounded, but offset pagination is not a frozen snapshot
  across separate requests.
- No editing, reopening, withdrawal, automated supersession, frontend or decision
  integration into search/ask. Historical approvals remain visible with freshness flags.
- Workspace permissions apply uniformly to sources and derived records. Existing
  production identity, document ACL, multipart-spooling and deployment limitations
  remain. In-flight requests may finish after token revocation; permission changes
  and review/extraction writers serialize on the workspace lock where necessary.
- Evidence immutability, cross-table workspace consistency and atomic review state
  are service/API guarantees. Privileged database operators remain unrestricted.
  Audit actor foreign keys prevent deleting referenced users; no HTTP user-deletion
  operation exists.

No external model, confidential fixture, external write, dependency addition, commit
or PR was used. Task 004 is implemented for human review before the next milestone.
