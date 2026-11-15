# Delivery plan

## Milestone 1: Knowledge Foundation

- Task 001: Synthetic document upload → parsing/chunking → persisted provenance → keyword retrieval → grounded response with source references.
- Task 002: Add semantic retrieval, hybrid ranking, evaluation cases.
- Task 003: Implement authenticated workspace access and verified permission filters.
- Task 004: Add knowledge extraction proposals and reviewer approval flow.

Tasks 001–002 are merged (PRs #1 and #2). Task 003 is implemented and awaiting
review; see [verification and limitations](docs/TASK_003.md).
Review Task 003 before beginning Task 004.

## Milestone 2: Team Knowledge Experience

- Frontend Q&A, knowledge browser, decision review queue, user feedback, source navigation.

## Milestone 3: Agent Harness

- Intent routing, context assembly, specialised read-only skills, bounded execution, evaluation, audit logs.

## Milestone 4: External Integrations

- One ACL-aware document connector, change detection, reindexing, deletion and revocation propagation.

## Development approach

For each task: write a concise plan, implement the smallest useful version, test, document trade-offs, request review before moving to the next task. Do not generate all milestones in one pass.
