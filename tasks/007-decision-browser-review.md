# Task 007 — Decision browser and review workflow

## Outcome

Workspace members browse approved decisions and verify pinned original evidence.
Editors/owners explicitly generate proposals from a latest source in Browse sources;
owners confirm approval or rejection, including their own proposals. Reuse Task 004
APIs and existing authentication. Ask remains the initial view.

## Contracts and behaviour

- Decisions are readable by every member; Review queue is editor/owner-only.
  Queue defaults pending with approved/rejected/all filters. Show exact quotations,
  existing actor UUIDs/timestamps, extraction provenance and terminal review comments.
- Lists display 20 rows, request 21 for lookahead, and retain server order. Page,
  filter and view changes clear details/drafts. Refresh retains filter, resets page.
- Shared Evidence extends to numbered Q&A citations. Verify workspace/source/version
  identities and exact Unicode code-point spans, preserving CRLF. Render all content
  and URI metadata as inert text. Historical decisions stay pinned.
- Generation posts the viewed source/version, never auto-approves, reports created
  and returned counts, and offers queue navigation. Historical versions cannot generate.
- Review requires explicit inline confirmation and optional trimmed comment. Omit
  blank comments; maximum 1,000 Unicode characters, no NUL. Approve only pending
  proposals with verified matching latest evidence; stale pending proposals remain
  rejectable. Backend freshness/locking remains authoritative.
- Disable duplicate writes. Terminal results are read-only and survive list-refresh
  failure. Refill the same filtered page after review, backing up if empty.
- Conflicts and uncertain review outcomes require proposal/source reconciliation
  before another confirmation. Never automatically repeat a review write.
- Reuse shared request abort/generation guards and memory-only session. Navigation
  clears drafts/confirmations; workspace/session/access loss clears protected state.
  Refresh roles on 403/404; readers leave the queue. Late responses are ignored.

## Acceptance

Component and real HTTP browser tests cover roles, generation, approval/rejection,
pagination, filters, Unicode/CRLF provenance, historical evidence, conflicts, retries,
uncertain outcomes, access loss, stale responses and inert hostile content. Existing
Q&A/browser regressions and configured web/Python/Docker checks pass. Integration
uses a dedicated PostgreSQL *_test database and removes only its synthetic fixtures.

No new HTTP contracts, migrations, dependencies, uploads UI, feedback, editable
interpretations, reopening/withdrawal, supersession, model calls, external writes,
integrations or retrieval changes. Freshness is a request-time snapshot; aborted
writes may still commit. Keep the current branch and do not commit without a request.
