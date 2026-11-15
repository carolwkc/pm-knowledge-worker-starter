# Product requirements — MVP

## Users

- Product manager: retrieve decisions, evidence, and product rationale.
- Designer: find user problems and research context.
- Tech lead: find implementation constraints and architectural decisions.
- Knowledge editor: review proposed knowledge records (later phase).

## Jobs to be done

- Find relevant product evidence quickly.
- Answer knowledge questions with verifiable sources.
- Trace decisions and product initiatives back to original inputs.
- See when evidence is missing or contradictory.

## Milestone 1 user story

As a team member, I can add synthetic product documents and query them, so that I can learn about a decision and verify exactly where the answer came from.

## Acceptance criteria

- Upload at least Markdown and plain-text files with source metadata.
- Store workspace ID, source ID, version, content hash, timestamps and chunks.
- Re-uploading identical source content is idempotent.
- Query returns ranked source excerpts with stable IDs and source locations.
- Answer endpoint can return deterministic extractive evidence if no LLM is configured.
- If LLM is configured, synthesis cites only retrieved source chunks; unsupported assertions are suppressed or flagged.
- Empty retrieval returns an explicit insufficient-evidence response.
- Queries require an authenticated user with workspace membership; no cross-workspace results.
- Workspace readers can search/ask, editors can also upload, and owners can manage memberships.
- Tests use synthetic fixtures and cover both successful and missing-evidence flows.

## Not yet in scope

SSO and production identity lifecycle, per-document ACLs, live document connectors, cross-tenant enterprise deployment, Slack/Jira writes, automatic knowledge promotion, complex graph UX, proactive monitoring.

## Quality targets for later pilot

- >=95% grounded answers with valid citations on a labelled benchmark.
- 0 cross-workspace retrieval leaks in security tests.
- >=85% retrieval recall@10 on curated questions.
- Accessible source citation navigation.

Targets are hypotheses to validate, not claims of current performance.
