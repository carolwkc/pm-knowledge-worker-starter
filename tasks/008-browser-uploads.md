# Task 008 — Browser uploads and source versions

## Outcome

Editors/owners add one new source or append one version from Browse sources using
existing authenticated ingestion APIs. Readers continue to browse original evidence.
Ask stays the initial view. Uploading never generates proposals or approves decisions.

## Contracts and behaviour

- Add source opens an inline title/optional URI/file form; Upload new version targets
  the selected scoped source, even from historical evidence, and accepts only a file.
  Explicit submit authorizes ingestion; choosing a file never sends it.
- Native input accepts `.md`, `.markdown`, `.txt` (case-insensitive). Client validates
  1–1,048,576 bytes, trimmed nonblank title up to 200 Unicode code points and optional
  trimmed URI up to 2,048 code points; metadata rejects NUL, blank URI is omitted.
  Server validates nonblank UTF-8/NUL-free text. Original File bytes stay unchanged.
- Typed multipart helpers return existing ingestion receipts. Preserve bearer,
  omitted credentials and no-store semantics. Browser supplies multipart boundaries;
  JSON callers retain their current headers and serialization.
- Reuse shared request/write guards. Disable duplicate writes and conflicting source
  controls while pending; permit view/workspace/disconnect navigation. Clear file,
  metadata and upload state on cancel, destination/session/scope/access changes.
  Abort and ignore late responses; abort does not promise server rollback.
- Verify receipt scope/shape before showing success. Store receipt before GETs, clear
  draft, reset catalogue filter/page, load destination history by source ID and open
  the exact returned version. Verify read identities/hash/version before showing text.
  Duplicate old hashes reuse historical versions without reactivating them.
- Preserve success on subsequent read failures; Retry runs GETs only. Access failures
  clear protected state and refresh authorization. Keep completed Q&A in its workspace.
- Fixed 413/415/422 messages retain correctable drafts. Never display server bodies.
  Network/server/unusable-receipt failures are uncertain; never replay a POST
  automatically. Offer catalogue inspection before explicit manual resubmission.
  Repeated new-source uploads can create separate documents; no exactly-once claim.
- Files, credentials, drafts and receipts remain in memory. All displayed content and
  URI metadata is inert; URIs are never fetched or navigated automatically.

## Acceptance

Transport/component and real HTTP Chromium tests cover roles, original multipart
bytes, metadata/file limits, Unicode/CRLF provenance, exact/historical receipt
navigation, deduplication, filter/page reset, off-page destinations, draft clearing,
access loss/demotion, late responses, safe validation, uncertain writes and GET-only
recovery. All existing Q&A/source/review tests and configured web/Python checks pass.
Use a dedicated PostgreSQL `*_test` database and remove only synthetic fixtures.

No new HTTP contracts, migrations, dependencies, backend idempotency, batch/drop
uploads, preview/progress, metadata editing, deletion, feedback, administration,
model calls or integrations. Keep the current branch; do not commit without request.
