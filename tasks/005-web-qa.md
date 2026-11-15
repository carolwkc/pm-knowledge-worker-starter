# Task 005 — Web Q&A with verifiable source evidence

## Outcome

A workspace member connects with an existing operator-issued token, asks a question,
and opens the original source version behind a structured citation. Use React,
TypeScript and Vite in `apps/web`, served by FastAPI in the production image.

## Implementation sequence

1. Add authenticated, workspace-scoped source-version reading. Return metadata,
   unchanged original text and computed freshness; preserve historical access.
   Apply `Cache-Control: no-store` to API responses, including errors.
2. Add connection, identity/logout, workspace selection, question/retrieval-mode form,
   verbatim answer, structured citation controls and original-source context panel.
3. Preserve Python Unicode offsets and CRLF when verifying a citation. Highlight
   only exact matches. Render all content as text and external URIs as inert metadata.
4. Keep token/answer/source state only in memory; abort requests and ignore late
   results on scope/session changes. Handle credential/access failures and refresh
   workspace discovery after access loss.
5. Build static assets in a Node stage; keep runtime non-root/Python-only. Serve
   root/assets only when a valid `WEB_DIST_DIR` is configured. Use a Vite API proxy
   during development without CORS changes or catch-all routes.
6. Exercise real credentials/provenance through API and Docker browser integration,
   plus UI state/race/error/security tests. Document setup and measured verification.

## Contracts and defaults

- `GET /api/v1/workspaces/{workspace_id}/sources/{source_id}/versions/{version_id}`
  returns `SourceVersionRead`: workspace/source/version UUIDs, `title`, nullable
  `external_uri`, `version_number`, `sha256`, `ingested_at`, `plain_text` and
  `source_is_latest`. Reader/editor/owner access; inaccessible or mismatched IDs are
  404; credential errors retain 401 with Bearer challenge. No schema migration.
- Connect validates `/me` before listing workspaces. Select the first joined
  workspace and show an explicit empty state when none exist. The token input clears
  immediately on submission; refreshing disconnects. No browser credential storage.
- Ask uses existing API defaults: keyword mode and limit 5. Semantic/hybrid are
  explicit selections; unavailable modes show an error without changing mode.
- Render server answers as text and build citation buttons only from `sources`.
  Fetch the cited version, verify workspace/source/version identity and exact
  code-point span before highlighting. Historical evidence remains inspectable.
- One current answer, no conversation persistence. Changing workspace clears question,
  answer and source state; a new question clears previous evidence. Disconnect/401
  also clears identity and credentials. Late successes and errors cannot restore it.
- Use npm with a committed lockfile; runtime needs no Node. Operator provisioning,
  uploads and membership administration remain existing API/CLI operations.

## Acceptance

- Real reader credentials can complete question → quoted answer → original evidence.
- Historical citations survive version updates; Unicode, emoji, CRLF and offsets
  remain unchanged. Unverified text is never highlighted.
- Cross-workspace and mismatched source/version reads fail; lost credentials/access
  clear protected UI state. Hostile source content cannot create executable HTML or links.
- Keyboard controls, source focus, loading/error announcements and narrow layouts work.
- Existing tests and configured checks pass; browser integration uses an explicitly
  selected test database and removes only its synthetic identities/workspaces.

No model calls, approval mutations, external writes, upload/review/browse/feedback
screens or production identity lifecycle. Keep the current branch; no commits
without explicit authorisation.
