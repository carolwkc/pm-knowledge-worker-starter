# Task 004 — Decision extraction proposals and approval

## Outcome

Explicitly extract deterministic, cited decision proposals from uploaded sources.
Workspace owners approve or reject immutable quotations; members read approved
decisions through a separate API. Search and ask continue to retrieve source evidence.

## Implementation sequence

1. Migration `0004` adds proposals, terminal review events and approved decisions,
   preserving all existing evidence, embeddings and access data.
2. `decision-marker-v1` proposes complete chunks beginning with case-insensitive
   `Decision:`, `We decided`, `We prioritised` or `We prioritized`, with nonblank
   following content. An optional Markdown heading prefix is ignored for matching
   only. Source text and offsets are never normalized or interpreted.
3. Editors/owners explicitly extract from a specified latest source version and
   inspect proposals. Workspace key-share then source update locking, together with
   chunk/extractor uniqueness, make generation
   repeatable without resetting review history or changing the original proposer.
4. Owners review, including their own proposals. Approval atomically records the
   review and creates one decision; rejection creates no decision. Same-action
   retries return the original result; opposite actions return 409.
5. Review locks workspace → source → proposal. Recheck ownership after workspace
   lock waits and freshness after source lock waits. Reject stale pending approvals;
   allow stale rejection and preserve prior approvals with a computed freshness flag.
6. Verify real-token permissions, concurrent requests, rollback, provenance and an
   isolated 0003 → 0004 → 0003 migration. Document contracts, walkthrough and results.

## Acceptance and defaults

- Readers see approved decisions; editors/owners also see all proposal statuses.
- Reuse the existing Evidence shape and 401/403/404 error conventions.
- All resource lookups and pagination operate inside the authorized workspace.
- Proposal list defaults to pending; status also accepts approved, rejected or all.
- Lists order by creation timestamp then UUID; limit defaults to 50, maximum 100;
  offset is nonnegative. Extraction results follow source chunk order.
- Review input accepts only action and optional comment (trimmed, nonblank when
  supplied, NUL-free, maximum 1,000 characters). Identity/time are server assigned.
- No external models, dependencies, source writes, frontend, editable interpretation,
  reopening, withdrawal, automatic supersession or integration into search/ask.
- Approval records review judgment, not factual truth. Sources remain untrusted data.
- Do not commit without an explicit request.

The approved implementation request is the specification. Verification and limitations
are recorded in [Task 004](../docs/TASK_004.md).
