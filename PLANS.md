# Delivery plan

## Milestone 1: Knowledge Foundation

- Task 001: Synthetic document upload → parsing/chunking → persisted provenance → keyword retrieval → grounded response with source references.
- Task 002: Add semantic retrieval, hybrid ranking, evaluation cases.
- Task 003: Implement authenticated workspace access and verified permission filters.
- Task 004: Add knowledge extraction proposals and reviewer approval flow.

Tasks 001–004 are merged (PRs #1, #2, #3 and #4).
See the historical [Task 004 verification and limitations](docs/TASK_004.md).

## Milestone 2: Team Knowledge Experience

- Task 005: Web Q&A with verifiable source evidence — React/TypeScript UI,
  authenticated workspace selection and immutable source-version navigation.
  See [specification](tasks/005-web-qa.md) and [verification](docs/TASK_005.md).
- Task 006: Source browser with title filtering and immutable version history.
  See [specification](tasks/006-source-browser.md) and [verification](docs/TASK_006.md).
- Later tasks: decision browser/review queue, user feedback and upload UI.

## Milestone 3: Agent Harness

- Intent routing, context assembly, specialised read-only skills, bounded execution, evaluation, audit logs.

## Milestone 4: External Integrations

- One ACL-aware document connector, change detection, reindexing, deletion and revocation propagation.

## Development approach

For each task: write a concise plan, implement the smallest useful version, test, document trade-offs, request review before moving to the next task. Do not generate all milestones in one pass.
