# Task 013 — Offline diagnosis of answer-support failures

## Outcome

Record the completed AI agent review of all 72 Task 012 responses separately from
human judgments. Produce reproducible evidence-linked diagnostics and an engineering
handoff without changing production retrieval, answers or thresholds.

## Contracts

- Preserve the complete Task 012 bundle and canonical blank human form byte-for-byte.
- Store AI verdicts, rationales and original document/codepoint spans, bound to the
  existing manifest/item IDs. Attribute the reviewer explicitly; unknown model is null.
- Add `uv run python -m pmknowledge.support_diagnostics --bundle DIR --ai-review PATH
  --output-dir DIR`. No database, network, inference, dependencies or migrations.
- Reuse bundle integrity checks, judgment validation and summary arithmetic without
  invoking the human-summary command or producing human-completion labels.
- Validate complete item coverage, manifest/rubric binding, AI provenance, nonpending
  verdicts (including uncertainty), rationales, original evidence bounds and verdict/
  response compatibility. Reject malformed JSON, duplicate keys and nonfinite numbers.
- Before writing, validate all inputs and construct both outputs. Write deterministic
  `diagnostics.json` and inert Markdown `report.md` into a new directory outside the
  input bundle. Refuse overwrite. Exit 0 indicates valid output, never quality; invalid
  input, existing directory or execution failure exits 2 with redacted diagnostics.
- Trace authored support and AI-cited evidence separately: original text/span,
  one-based candidate ranks and emitted citation numbers using full-span containment.
  Empty reference lists do not establish corpus absence or answerability.
- Distinguish candidate gaps from selection gaps, with separate AI-evidence tags.
  Combine AI judgments with status/category for missing-fact/conflict grounded tags;
  report overlapping findings without summing them as disjoint failures.

## Findings and acceptance

Reproduce 29 fully supported, 1 partially supported, 24 unsupported and 18 conflicting
AI judgments, across 72 grounded answers and no abstentions. Inspect all modes and
categories. Link recommendations to item IDs; distinguish observations from hypotheses.

Cover semantic PipitDock multi-04's retrieved-but-omitted escalation quotation;
CobaltNest/EmberQuay multi-05/06's missing retention values among all five candidates;
all missing-fact/conflict-resolution questions; and successful direct/multi-source
controls. Asking for both positions is different from resolving one authoritative
position. Candidate-only reranking cannot recover absent evidence.

Test reference validation, tampering, traces, Unicode/CRLF, inert Markdown,
deterministic reproduction, no overwrite and CLI errors. Run full backend,
documentation, Ruff lint/format and mypy checks; record actual results. Update README,
roadmap and capabilities documentation.

## Boundaries

One AI reviewer, synthetic observed data, no human agreement or independent semantic
validation. Mechanical span checks cannot establish judgment truth. No policy tuning,
release gate, production API/UI/schema change, automated promotion, external writes,
commits or branch rename. Future changes require a concrete alternative and fresh
frozen validation plus permission/provenance checks.
