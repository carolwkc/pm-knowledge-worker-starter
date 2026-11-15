# Task 008 — Browser uploads and source versions

## Delivered

- Editor/owner Add source form and source-scoped Upload new version action in Browse
  sources. Native single-file selection requires explicit submit; historical source
  views can append versions without changing metadata or old evidence.
- Original `File` multipart transport, typed ingestion receipts, browser-set boundaries
  and unchanged JSON/authentication/no-store behavior. Client checks file extension/size
  and Unicode metadata limits; backend remains authoritative for text validation.
- Receipt saved before refresh reads, filter/page reset, exact returned-version display
  and history loaded independently of the catalogue page. Historical duplicates retain
  their original identity and never reactivate old content.
- GET-only recovery after confirmed save, safe validation messages and explicit uncertain
  upload handling with catalogue inspection. No automatic upload POST retries.
- Shared synchronous write guard, request abort/generation checks, memory-only file/drafts,
  navigation clearing and detected access-loss/role refresh. Completed Q&A stays pinned.

Specification: [Task 008](../tasks/008-browser-uploads.md).
Walkthrough: [README](../README.md#task-008-upload-documents-and-new-versions).

## Verification

Executed on 2026-11-15 using locked dependencies, Python 3.12.12 and the existing
PostgreSQL 16/pgvector image. Dedicated Compose project `minnetonka-task008` uses
database port 55438, API port 58008 and `pmknowledge_test`. Other projects/volumes
were untouched; no `.env` files, backend contracts, migrations or dependencies changed.

| Check | Result |
| --- | --- |
| `uv sync --dev --frozen`, web `npm ci` | Passed |
| Dedicated-database `uv run pytest -q` | 158 passed |
| `uv run ruff check .`, `uv run ruff format --check .` | Passed |
| `uv run mypy apps/api/src` | Passed, 14 source files |
| Web `npm test` | 119 passed: 75 existing and 44 upload tests |
| Web `typecheck`, `lint`, `format:check`, `build` | Passed |
| Dedicated-database `uv run alembic check` | No new upgrade operations |
| Docker build and health | Passed |
| Real HTTP Chromium integration | 9 passed |
| Browser fixture cleanup | Zero browser users/workspaces remaining |
| Runtime UID | 10001 |
| `git diff --check` | Passed |

The initial upload test run had 25 failures on missing controls/methods and one
existing reader behavior passed. Implementation made those behaviors pass. Expanded
coverage verifies multipart File identity, preserved JSON requests, explicit submit,
roles, old-version reuse, extension and exact 1 MiB boundaries, Unicode code-point
metadata limits/NUL rejection, cancellation/destination changes, 413/415/422 handling,
confirmed success across each refresh failure, GET-only retries, uncertain or invalid
receipts, mismatched exact-version responses, filter/page reset with an off-page
destination, access loss/demotion and delayed success/401/404 after scope changes.

Real HTTP tests upload synthetic Unicode/CRLF/hostile text through the browser, ask
and inspect citations, append a changed version, reuse historical content, preserve
the latest version and verify no automatic proposal generation. Readers inspect
history without upload controls, receive 403 on both upload APIs and cannot read a
foreign-workspace source. Further coverage exercises invalid UTF-8 and editor demotion
with a prepared upload. Existing seven browser regressions remain intact. Keyboard
operation, a 390px viewport, inert URI/content and empty browser storage are checked.

Early verification caught unsupported Testing Library options and a mock catalogue
incorrectly scoped to the previous workspace; both test fixtures were corrected.
The first browser run passed eight tests and timed out after keyboard activation of
a temporarily disabled Add source button. Its page snapshot showed focus still on
Browse sources. Waiting for the catalogue's enabled control before keyboard activation
resolved the test race; the complete nine-test run then passed. The Playwright
NO_COLOR/FORCE_COLOR warning is unchanged and does not represent a failure.

An optional synthetic-only upload form screenshot was captured and inspected at
`.context/upload-form.png`. Automatic screenshots, traces and videos remain disabled.

## Independent review

A fresh read-only reviewer inspected the uncommitted implementation, specification
and tests, and independently ran the 44 upload tests successfully. They found no
actionable Critical, Important or Minor issues and declined no behavior as out of
scope. Database/browser results above come from the implementing session.

## Limitations and operation

- No backend idempotency keys: a lost response can conceal a committed new source,
  and a deliberate repeat can create a separate document. Inspect the catalogue
  before resubmitting. Existing-source versions deduplicate content by hash.
- An aborted request may commit. There is no server cancellation, exactly-once
  guarantee, upload progress, frozen pagination or polling. Freshness is read-time.
- Access changes clear already received data only after a request detects them or
  the session/scope is cleared. Browser developer tools can inspect tab memory.
  Production SSO, identity lifecycle and per-document ACLs remain deferred.
- Files remain limited to the existing UTF-8 Markdown/text contract and 1 MiB bound.
  Content validation happens at the server, so invalid text may be sent then rejected.
- Browser integration targets Chromium; keyboard/narrow-layout coverage is not a
  claim of complete assistive-technology or cross-browser conformance.
- No batch/drop upload, preview, metadata editing, deletion, feedback, administration,
  external model calls, integrations, external writes, commits or branch rename.

The dedicated API/database remain available at `http://127.0.0.1:58008`, with browser
fixtures removed. Reproduce all checks using the README. To stop only this project
and preserve its volumes:

```sh
POSTGRES_PASSWORD=localdev POSTGRES_PORT=55438 API_PORT=58008 \
  docker compose -p minnetonka-task008 -f compose.yaml -f apps/web/e2e/compose.yaml down
```
