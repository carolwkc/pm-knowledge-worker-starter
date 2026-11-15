# Task 007 — Decision browser and review workflow

## Delivered

- Decisions navigation for all members and an editor/owner proposal queue with
  pending/approved/rejected/all filters, 20-item pages and bounded 21-row lookahead.
- Explicit generation from the viewed latest source, created/returned counts,
  no-match/repeat outcomes and queue navigation. No automatic approval.
- Owner-only inline review confirmation with Unicode-aware comment validation,
  verified current evidence before approval and rejection of stale proposals.
- Shared source Evidence supports decision/proposal context without fabricated
  Q&A numbering. Original Unicode/CRLF text, offsets and pinned versions survive
  source updates. Actor attribution uses the API's stable user UUIDs.
- Terminal record preservation, queue refill/backtracking and independent read
  retries. Conflicts and uncertain writes reconcile through proposal/source reads;
  no review POST is automatically repeated.
- Memory-only session/drafts and shared abort/generation guards. Access failures
  clear protected state and refresh roles; demoted readers leave the queue.

Specification: [Task 007](../tasks/007-decision-browser-review.md).
Walkthrough: [README](../README.md#task-007-generate-review-and-browse-decisions).

## Verification

Executed on 2026-11-15 with locked dependencies, Python 3.12.12 and the existing
PostgreSQL 16/pgvector image. Dedicated Compose project `ashgabat-task007` uses DB
port 55437, API port 58007 and `pmknowledge_test`. Other workspace projects and
volumes were untouched; no `.env` files were changed.

| Check | Result |
| --- | --- |
| `uv sync --dev --frozen`, web `npm ci` | Passed |
| Dedicated-database `uv run pytest -q` | 158 passed |
| `uv run ruff check .`, `uv run ruff format --check .` | Passed |
| `uv run mypy apps/api/src` | Passed, 14 source files |
| Web `npm test` | 75 passed |
| Web `typecheck`, `lint`, `format:check`, `build` | Passed |
| Dedicated-database `uv run alembic check` | No new upgrade operations |
| Docker build and health | Passed |
| Docker Chromium integration | 7 passed |
| Browser fixture cleanup | Zero remaining browser users/workspaces |
| Runtime UID | 10001 |
| `git diff --check` | Passed |

The initial seven workflow tests failed on missing navigation, then passed with
the implementation. The full UI suite retains all 42 prior tests and adds 33.
Coverage includes role controls, confirmation/cancellation, exact Unicode/CRLF
evidence, identity/span/statement mismatches, stale approval/rejection, generation
no-match/repeat/conflict outcomes, comment boundaries, uncertain/conflicting review
recovery, terminal-result retention, page backtracking, demotion and delayed review
success/401/404 responses after view/workspace/logout changes.

Real HTTP tests exercise editor generation, repeated extraction without duplicate
proposals, owner approval, a concurrent source update causing 409, stale rejection,
reader historical evidence inspection, hidden/forbidden controls, cross-workspace
concealment, token revocation and owner demotion. Existing Q&A/source-browser tests
remain intact. Keyboard source navigation, exact highlighting, inert URI metadata,
a 390px viewport and empty browser storage are checked. Optional synthetic-only
screenshot: `.context/decision-review.png`. Automatic traces/videos/screenshots
remain disabled.

The first Docker build exposed invalid Testing Library test options; the options
were corrected before the passing build. An intermediate late-response test fixture
returned a foreign-workspace record for the newly selected workspace; correcting the
fixture left the production mismatch guard intact. Existing npm dependency-deprecation
and Playwright colour-setting warnings do not represent test failures. A subsequent
browser run exposed an owner fixture with two workspaces and tied creation times:
the test assumed Aurora was selected, but the snapshot showed Orbit. New browser
flows now explicitly select their seeded workspace instead of relying on list order.

## Independent review

A fresh read-only reviewer found one minor queue-refresh defect: after an uncertain
review response, a reconciled terminal detail could leave its old pending queue row
visible. A new last-page regression failed against that behaviour, then passed after
sharing queue refill/backtracking between successful and reconciled reviews. Failed
reconciliation retries also retain that refill requirement. Terminal details survive
list failure, and retries remain reads only.

The reviewer checked the correction and reported no further findings. They did not
run tests or touch the database. Recorded verification results come from the
implementing session; final web checks and Docker browser integration were rerun
after the correction.

## Limitations and operation

- The marker extractor nominates exact quotations, not semantic interpretations.
  It can nominate misleading text and miss implicit decisions; human review does
  not establish factual truth. No extraction-quality improvement is claimed.
- Freshness is a request-time snapshot. Server-side locking is authoritative when
  sources change after browser reads. No polling, frozen pagination, automatic
  supersession, reopening, withdrawal or editing is introduced.
- An aborted browser request can still commit on the server. Refresh on return to
  inspect the recorded result. An uncertain review requires successful reads and a
  new confirmation before another submission; original terminal attribution wins.
- Workspace-wide permissions and operator-issued tokens remain unchanged. Already
  received content clears only after detected access loss/session reset. Browser
  developer tools can inspect in-memory data. No SSO, per-document ACLs or production
  identity lifecycle is added.
- Automated browser coverage targets Chromium. Keyboard/narrow-layout tests do
  not establish full assistive-technology or cross-browser conformance.
- No new endpoints, migrations, dependencies, model calls, external writes,
  upload/feedback/admin UI or retrieval changes. No commits or branch rename.

Reproduce setup/checks using the README's dedicated-project commands. The test
API/database remain available at `http://127.0.0.1:58007`; synthetic test fixtures
have been removed. Stop only this project while preserving volumes with:

```sh
POSTGRES_PASSWORD=localdev POSTGRES_PORT=55437 API_PORT=58007 \
  docker compose -p ashgabat-task007 -f compose.yaml -f apps/web/e2e/compose.yaml down
```
