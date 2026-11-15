# Task 006 — Source browser with version history

## Delivered

- Authenticated, workspace-scoped source catalogue and version-history metadata APIs,
  literal case-insensitive title filtering and bounded pagination with `has_more`.
  Latest versions use version numbers; re-uploading old content cannot reactivate it.
- Ask/Browse navigation, 20-item catalogue/history pages, explicit filter/clear/refresh
  controls, exact latest/history reads and operation-specific errors/retries.
- Shared immutable viewer supports direct text inspection without invented citation
  evidence; Q&A retains identity/span validation and exact quotation highlighting.
- Session/workspace/view changes abort and invalidate pending requests. Access loss
  clears browser data, including unsent filter drafts, and refreshes memberships.
  No browser storage, source mutations, external calls, migrations or new dependencies.

Specification: [Task 006](../tasks/006-source-browser.md).
Reproducible setup and walkthrough: [README](../README.md#task-006-browse-original-sources-and-version-history).

## Verification

Executed on 2026-11-15 using locked dependencies. Dedicated Compose project
`canberra-task006` uses database port 55436, HTTP port 58006 and the disposable
`pmknowledge_test` database. Existing workspace containers/volumes and `.env` files
are untouched.

| Check | Result |
| --- | --- |
| `uv sync --dev --frozen`, web `npm ci` | Passed; npm reported zero vulnerabilities |
| Dedicated-database `uv run pytest -q` | 158 passed |
| `uv run ruff check .`, `uv run ruff format --check .` | Passed |
| `uv run mypy apps/api/src` | Passed, 14 source files |
| Web `npm test` | 42 passed |
| Web `npm run typecheck`, `lint`, `format:check`, `build` | Passed |
| `uv run alembic check` against dedicated database | No new upgrade operations |
| Docker build and health checks | Passed |
| Docker Chromium integration | 5 passed |
| Browser fixture cleanup | No remaining synthetic browser users/workspaces |
| Runtime UID / Node lookup | UID 10001; Node absent |
| `git diff --check` | Passed |

The first API regression failed with 405 on the absent listing route. All 10 new
browsing tests then passed. The first UI regression failed on absent navigation;
existing Q&A remained green. Additional coverage reproduced an unsent title filter
surviving access loss; moving draft state into the shared reset boundary fixed it.
An initial Q&A preservation assertion used whitespace-normalized text matching;
the corrected assertion checks exact DOM text and verified highlight behavior.

API coverage includes roles, concealed foreign/mismatched resources, membership
removal, revoked/missing credentials, timestamp ties, pagination, `%`/`_`/escape
matching, invalid filters, old-hash uploads, historical reads and metadata-only lists.
Component tests include filtering/history, Q&A preservation, inert hostile content,
response identity, retries, access-loss clearing and delayed successes/401/404
responses after view/workspace/session changes.

Real-browser integration retains all three Task 005 scenarios and adds catalogue
pagination across 21 documents, literal title filtering across pages, latest and
historical reads with exact Unicode/CRLF, absent fabricated highlights/chunk IDs,
inert URI provenance, source-heading focus, keyboard filtering, a 390px viewport,
empty browser storage, reload disconnection and membership-revocation clearing.
The optional screenshot contains only the synthetic browsing session, stored in
`.context/source-browser.png`.

npm prints the existing transitive `whatwg-encoding` deprecation; Playwright prints
an environment colour-setting warning. Neither is a test failure.

## Independent review

A fresh read-only reviewer found no Critical or Important issue in SQL scoping,
immutable identities, request invalidation, citation verification or inert rendering.
They identified two minor error-state gaps: failed history could display an empty-page
message, and errors did not identify the failed browsing operation. Both were fixed
as part of the required accurate, operation-specific failure behaviour.

Three new regression scenarios failed against the generic errors, then passed after
adding catalogue/history/source labels and successful-history-load state. Retry now
recovers each operation; failed history never masquerades as a successful empty page.
The complete 42-test UI suite, lint, format, typecheck and build passed after the fixes.
The reviewer did not run tests or touch the database; reported execution results here
come from the implementing session. Docker integration was rerun against the final build.

## Limitations

- Workspace-wide permissions and operator-issued tokens remain the identity model;
  no document ACLs, signup, SSO, TLS deployment or production identity lifecycle.
- Freshness is a request-time snapshot. Refresh discovers changes; offset pages may
  shift during concurrent uploads. There is no polling or cached permission state.
- Already rendered content is cleared only when a request detects access loss or
  the session is reset. Browser/developer tools can access in-memory content.
- Metadata lists exclude text, but exact-version reads return the full original
  source under existing workspace permissions and the existing 1 MiB upload limit.
- Title matching is a database case-insensitive substring, not semantic or document
  content search. Unicode case folding follows PostgreSQL's configured locale.
- Automated browser coverage targets Chromium. Keyboard/narrow-layout tests do not
  establish full assistive-technology or cross-browser conformance.
- Uploads, decision browsing/review, feedback and administration remain API/CLI
  operations. No retrieval/extraction quality improvements are claimed.

Implementation verification was completed before commit/PR creation, without a
branch rename, external model or external write.

The isolated API/database are left running at `http://127.0.0.1:58006` for inspection;
browser fixtures were removed. Provision a synthetic session using the README CLI
workflow. To stop these containers while preserving their volumes:

```sh
POSTGRES_PASSWORD=localdev POSTGRES_PORT=55436 API_PORT=58006 \
  docker compose -p canberra-task006 -f compose.yaml -f apps/web/e2e/compose.yaml down
```
