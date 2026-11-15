# Task 005 — Web Q&A and source navigation

## Delivered

- React/TypeScript/Vite interface: existing-token connection, joined workspace
  selection, explicit keyword/semantic/hybrid Q&A, verbatim answers and structured
  citation controls. One current answer; no browser storage or saved conversations.
- Reader-authorised source-version API with explicit workspace/source/version joins
  and unchanged original text. Historical evidence stays readable with computed
  freshness. No migration, model calls or approval/external writes.
- Original-source panel verifies the cited version identity and Unicode code-point
  span before highlighting. CRLF/emoji remain intact. Text is escaped; external URIs
  are inert metadata. Source heading receives focus for keyboard navigation.
- Requests are aborted and generation-checked when scope/session changes; old
  successes/errors cannot restore cleared state. Credential failures disconnect;
  access failures clear evidence and refresh joined workspaces.
- Optional host static build plus same-origin Docker UI. Build stages install npm
  dependencies; runtime stays Python-only and UID 10001. API routes/docs retain
  their existing paths. API responses, including unexpected errors, use no-store.

Specification: [Task 005](../tasks/005-web-qa.md). Reproducible commands and browser
walkthrough: [README](../README.md#task-005-ask-and-inspect-evidence-in-the-browser).

## Verification

Executed on 2026-11-15 with locked Python dependencies, Node 25.2.1/npm 11.6.2
on the host and Node 24 in Docker. PostgreSQL/pgvector uses the isolated Compose
project `buenos-aires-task005`, database port 55434, HTTP port 58002. Other workspace
containers/volumes and local `.env` files were left untouched.

| Check | Recorded result |
| --- | --- |
| `uv sync --dev --frozen` | Installed locked dependencies |
| Dedicated-database `uv run pytest -q` | **148 passed** |
| `uv run ruff check .` | Passed |
| `uv run ruff format --check .` | Passed |
| `uv run mypy apps/api/src` | Passed, 14 source files |
| Web `npm run typecheck`, `lint`, `format:check`, `build` | Passed |
| Web `npm test` | **17 passed** |
| `npm audit --audit-level=moderate` | No reported vulnerabilities |
| Docker build and Compose health checks | Passed |
| Runtime `id -u` / Node lookup | UID 10001; Node absent |
| Docker Chromium integration | **3 passed** |
| `uv run alembic check` against dedicated database | No new upgrade operations |
| Live root/health/docs/OpenAPI and 401/404 smoke | Passed; API errors retain no-store |
| Browser fixture cleanup | No remaining synthetic browser users/workspaces |
| Vite development source serving and `/api` proxy | Passed; proxied 401 retains Bearer/no-store headers |
| `git diff --check` | Passed |

The real-browser integration uses operator-provisioned reader/owner credentials,
synthetic workspaces and real uploads. It checks question → evidence → original
context, exact emoji/CRLF text/highlight, historical navigation after a new upload,
foreign/mismatched resource denial, inert URI metadata, empty browser storage and
reload disconnection. Additional scenarios cover insufficient evidence, unavailable
semantic mode without fallback, token revocation, keyboard connection and a 390px
viewport without horizontal overflow. Each test removes its own synthetic rows.
The test helper refuses databases not explicitly configured with an `_test` suffix.

API tests cover reader/editor/owner access, membership removal, absent/revoked
credentials, scoped resource combinations, unchanged historical provenance and
cache headers on success/401/404/422/500 responses. Component tests cover hostile
source/answer text, invalid spans, empty workspaces, access refresh, network/validation
failures and late responses after scope/session changes.

The first API regression run failed on the absent endpoint/static support; the first
UI run failed on absent connection/evidence behaviour. The implementations passed
their corresponding suites. A later regression reproduced unexpected 500 responses
bypassing normal response middleware; the safe exception handler fixed its no-store
header. Initial browser failures were ambiguous test locators matching both the
workspace selector and question form; exact locators passed all three scenarios.

The npm lock contains a scoped override from the TypeScript lint parser to patched
`minimatch` 11; without it npm reported a moderate transitive denial-of-service
advisory. Vitest 4.1.12 avoids the critical advisories from the initial older test
tooling. Lint/build/tests run against the resolved override. npm prints a transitive
`whatwg-encoding` deprecation; Playwright prints an environment colour-setting
warning. Neither is a test failure.

## Independent review

A fresh reviewer inspected the uncommitted implementation, including untracked files,
and found no Critical or Important issue. They independently ran all 17 UI tests,
the TypeScript check and diff whitespace check successfully; they did not rerun the
database/browser suites. They reviewed permission scoping, source/span identity,
late-result guards, access-loss clearing, no-store errors and static/Docker serving.

One minor setup mismatch was corrected: declared/documented Node support now matches
the lint tooling (`^22.13.0 || >=24`), including lockfile metadata. Full assistive
technology/cross-browser conformance, enabled-semantic browser coverage and production
identity/TLS/scaling remain explicitly deferred rather than review guarantees.

## Limitations

- Operator-issued tokens remain the local identity mechanism; no SSO, signup,
  production identity lifecycle or TLS deployment. Do not expose this local setup
  as a production service. Token memory is accessible to trusted browser extensions
  and developer tools; existing workspace-wide permissions also apply to full text.
- Revocation is checked per request. Already rendered text cannot be retracted until
  a subsequent request detects access loss or the session is cleared. No polling,
  cross-tab session sharing, service worker or persisted cache is introduced.
- Source viewing returns the full uploaded version, bounded by the existing 1 MiB
  upload limit. Latest-version status is a snapshot at read time. The UI does not
  automatically refresh source freshness or reinterpret evidence.
- Semantic/hybrid success remains covered by existing backend tests; browser tests
  deliberately run offline with embeddings disabled. No new extraction or retrieval
  quality claim is made. Matching quotations may not answer a question or be true.
- Chromium is the automated browser target. Keyboard/narrow-layout tests do not
  establish full assistive-technology or cross-browser conformance.
- Upload, browse, review queue, feedback and membership screens remain deferred.
  Existing API/CLI workflows supply data and access.

Implementation verification was completed before commit/PR creation, without a
branch rename or external write. The isolated Docker API/database remain
running at `http://127.0.0.1:58002` for inspection, against the disposable test
database. Browser fixture identities were removed; use the README provisioning
workflow to create your own local synthetic session. The temporary Vite process
used for proxy verification was stopped.
