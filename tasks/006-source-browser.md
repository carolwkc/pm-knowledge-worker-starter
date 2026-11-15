# Task 006 — Source browser with version history

## Outcome

Workspace members browse original documents, filter titles and inspect latest or
historical versions without asking a question. Reuse the React interface, existing
token authentication and immutable source-version API. Q&A remains the initial view.

## Contracts

- `GET /api/v1/workspaces/{workspace_id}/sources` returns `{sources, has_more}`.
  Each summary contains workspace/source UUIDs, title, nullable external URI,
  creation timestamp and latest-version UUID, number and ingestion timestamp.
- `GET /api/v1/workspaces/{workspace_id}/sources/{source_id}/versions` returns
  `{versions, has_more}`. Each row contains workspace/source/version UUIDs,
  version number, SHA-256, ingestion timestamp and computed `source_is_latest`.
- Metadata lists exclude document text. Both use `limit` (default 50, range 1–100)
  and nonnegative `offset`, fetching one extra row for `has_more`. Sources sort by
  creation time descending then UUID ascending; versions sort by number descending.
- Optional `title` uses a trimmed case-insensitive literal substring, maximum 200
  characters. Blank means unfiltered; reject NUL. `%`, `_` and the escape character
  are literal. Filtering and pagination follow SQL workspace/membership constraints.
- Readers/editors/owners may browse. Preserve 401/Bearer, 404 resource concealment,
  422 validation and no-store responses. No migration or dependency additions.

## Browser behaviour

1. Add Ask/Browse sources navigation below the workspace selector. The browser uses
   20-item pages, an explicit filter form, Clear, Refresh and Previous/Next controls.
2. Selecting a document fetches its first history page and opens its newest returned
   version. History paging preserves the displayed text; version selection reads the
   selected immutable UUID. Show timestamps and latest/historical labels.
3. Filter, catalogue-page and refresh actions clear detail. Refresh retains the
   applied filter and resets pagination. View changes abort work and clear browsing
   and open source state; completed Q&A remains within the same workspace.
4. Direct reads show exact text and provenance without invented citations/highlights.
   Q&A still verifies source identity and Unicode spans before highlighting.
5. Keep state in memory. Workspace changes clear both experiences, including filter
   drafts. Disconnect/401 clear the session. On 403/404 clear protected state and
   refresh joined workspaces. Abort and generation checks ignore late successes/errors.
6. Provide operation-specific errors and explicit retries, empty/no-match/loading
   states, keyboard controls, focused source headings and narrow layouts. All text
   and URI metadata remain inert.

## Acceptance and boundaries

API tests exercise roles, isolation, revocation, filtering, pagination, validation,
latest selection and metadata-only results. Component tests exercise browsing,
history, retries, hostile content, mismatched identity, scope/session races and Q&A
regressions. Real-browser integration uses synthetic identities/uploads in an
explicit `_test` database and cleans up only its fixtures. Run configured Python/web
checks, Docker integration and Alembic drift detection; document actual outcomes.

No source mutations, uploads, decision browsing/review, feedback, model calls,
integrations, routing dependencies or production identity changes. Freshness is a
request-time snapshot; offset pagination may shift during concurrent uploads.
Keep the existing branch and make no commits without an explicit request.
