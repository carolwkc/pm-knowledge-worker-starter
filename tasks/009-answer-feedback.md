# Task 009 — Q&A feedback and owner inspection

## Outcome

Members explicitly submit Helpful/Not helpful feedback on completed quoted or
insufficient-evidence answers. Owners inspect saved user-reported context and exact
citations. Ordinary questions remain unsaved; feedback never becomes approved knowledge.

## Contracts

- Persist question/mode captured when asking, answer snapshot, authenticated author,
  rating, optional negative reason (missing_evidence/irrelevant_evidence/other), optional
  trimmed NUL-free comment up to 1,000 Unicode characters, submission UUID and timestamp.
  Helpful feedback has no negative reason; blank comments become absent.
- Any member POSTs workspace-scoped feedback. Owners alone GET paginated summaries
  (rating filter, newest timestamp/UUID first, limit/offset/has_more) and full detail.
  Initial creation is 201; identical normalized retries return 200 and original receipt;
  changed payloads using the same workspace/author/submission UUID return 409 atomically.
- Validate at most three exact immutable citations through workspace-scoped joins.
  Foreign/missing references receive generic 404. Historical evidence is valid. Quote
  formatting and insufficient-evidence messages use the existing pure answer composer.
  Valid citations do not prove this response was returned for this reported question.
- Bound input fields, reject unexpected fields and preserve safe errors, no-store
  responses and logs without content. Migration 0005 preserves existing data.
- Explicit Submit feedback discloses saved context and owner visibility. Disable
  duplicate submissions for the completed answer; freeze uncertain submissions and
  offer explicit same-payload/same-UUID Retry, never automatic write retries.
- Owner Feedback view uses 20-item pages, rating filter, Refresh, summary attribution,
  full user-reported context and original-version citation navigation/highlighting.
- Reuse cancellation/generation/write guards and permission refresh. Clear unsent
  drafts on view changes; preserve completed Q&A/submission status within a workspace.
  New questions, workspace/session changes and detected access loss clear Q&A/feedback.
  Owner demotion removes the view. All content remains inert and browser state memory-only.

## Acceptance and boundaries

Backend, migration, component and real-HTTP Chromium tests cover scoped access,
historical/fabricated evidence, Unicode and limits, concurrent idempotency, uncertainty,
edited-question isolation, paging, cancellation and permission loss. Run configured
Python/web checks and dedicated PostgreSQL *_test integration. Use synthetic data only.

No editing/deletion/resolution, analytics, external models/integrations, new dependencies,
automatic knowledge changes, commits or branch rename. Snapshots persist until their
workspace is removed, including after privileged source removal; no retention UI exists.
