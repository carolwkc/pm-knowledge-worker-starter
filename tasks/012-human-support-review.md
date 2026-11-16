# Task 012 — Human review of requested-fact support

## Outcome

Deliver an offline Markdown-and-JSON workflow and a fresh review-ready synthetic
cohort. Human findings remain pending. Do not change production retrieval, answer
selection, thresholds, HTTP interfaces or stored knowledge.

## Contracts

- Author twelve documents and twenty-four questions, six each direct support,
  multi-source support, missing specific facts and unresolved conflict resolution.
  Use existing dataset schemas and exact support spans. Include numeric controls,
  topical distractors, Unicode/CRLF and untrusted source instructions. Freeze the
  corpus hash before evaluation; preserve previous data/artifacts and never tune.
- Capture the current selected policy at k=5 in keyword, semantic and hybrid modes,
  using the existing rollback-only evaluator and cached local encoder.
- Add `uv run python -m pmknowledge.support_review export --cases PATH --report PATH
  --output-dir DIR` and `summarize --bundle DIR --judgments PATH`.
- Require a complete passing v3 capture bound to the corpus and the frozen Task 011
  production policy, all three modes, the existing model and semantic floor 0.6.
  Reuse existing nested capture checks; do not trust a top-level success alone.
- Export only into a new directory: exact corpus/capture copies, inert `packet.md`,
  immutable `manifest.json` and editable blank `judgments.json`. Bind stable question/
  mode identities to input hashes. Revalidate original inputs and rebuilt immutable
  packet/manifest when summarizing. Reject changed bindings or duplicate/missing IDs.
- Show 72 items with question, actual selected response, exact quotations, citation
  identities and original offsets. Include the full original corpus. Omit gold
  labels, legacy answers and automated quality scores from the packet. All dynamic
  source content must remain inert even when it contains HTML or Markdown fences.
- One reviewer per judgment file. Fields are reviewer ID, item ID, nullable verdict,
  rationale and original document/character spans. No automated human labels.

## Human rubric and summaries

Verdicts: fully supported, partially supported, unsupported, conflicting, justified
abstention, unjustified abstention or uncertain. Null is pending. Submitted judgments
require a rationale and reviewer ID. Full/partial support needs evidence inside
displayed quotations; unjustified abstention needs supporting corpus evidence.
Conflict needs distinct, non-overlapping spans for both opposing positions, which
may include omitted documents. All supplied references must select original text.

Full support requires every requested fact in displayed quotations and no unresolved
contradiction elsewhere in the corpus for the same scope/time. Conflict overrides
full/partial support. Explicit resolutions or differing scopes/times do not establish
conflict. Questions asking for both positions may be fully supported by quoting both.
The tool validates references and response-status compatibility, not semantic truth.

Summaries include completion, uncertainty and verdict counts overall/by mode/category,
follow-up item IDs and full-support rates with counts/null empty denominators. Rates
exclude pending, uncertain and abstaining items. Blank templates say human review
pending; completed forms do not mean quality passed. Exit 0 means a valid export or
summary, including incomplete review. Invalid input/execution exits 2 with redacted
diagnostics. No quality gate or policy promotion occurs.

## Acceptance and boundaries

Test frozen corpus shape, deterministic binding, tampering, invalid spans, labels,
partial reviews, metrics, Markdown safety and original Unicode/CRLF. Add a controlled
encoder integration test from ingestion through evaluation/export/summary and assert
fixture rollback. Synthetic test judgments must never appear as human findings.

Record a real offline all-mode capture and canonical blank bundle. Run full backend,
documentation, Ruff, mypy and dedicated-database Alembic checks. Update README, roadmap,
capabilities and Task 012 verification notes. Human review itself is not required for
completion. No dependencies, migration, production UI/API, model changes, external
inference, feedback mining, automatic promotion, commits or branch rename.
