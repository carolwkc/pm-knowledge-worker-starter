# Task 013 — Offline AI support diagnosis

## Delivered

The [AI review](evaluations/task-013-ai-review.json) transcribes the completed
`/root/packet_review` agent's assessment of all 72 Task 012 responses and twelve original
documents. Model identity was not exposed and is recorded as null. The review was
recorded on 18 November 2026; no exact review time is asserted. The Task 012 bundle,
including its blank human judgments, is preserved. No inference runs inside this CLI.

The [diagnostic report](evaluations/task-013-diagnostics/report.md) and
[machine-readable traces](evaluations/task-013-diagnostics/diagnostics.json) preserve
the distinction between authored dataset labels, AI semantic judgments and mechanical
span containment. Neither a valid reference nor an AI verdict proves semantic truth.

Specification: [Task 013](../tasks/013-support-diagnostics.md).

## Reproduce offline

After `uv sync --dev --frozen`, run from the repository root:

```sh
uv run python -m pmknowledge.support_diagnostics \
  --bundle docs/evaluations/task-012-review \
  --ai-review docs/evaluations/task-013-ai-review.json \
  --output-dir .context/task013-diagnostics
```

Choose a new output directory outside the input bundle each time. Outputs are
byte-identical for identical inputs; no current timestamp or machine-local path is
added. The receipt lists hashes of both output files. No database or model is needed.
Exit 0 means valid output, not quality passed; invalid input, existing output or an
execution failure exits 2 with redacted diagnostics. A disk/write failure may leave
a partial directory; inspect it and choose a new destination rather than overwriting.

## Review and report formats

AI review schema version 1 extends the existing judgment fields (`manifest_sha256`,
`reviewer_id`, `items`) with `review_kind: "ai"` and `provenance`: `agent_id`, nullable
`model`, `review_date`, `method`, and `rubric_sha256`. The rubric hash binds the exact
Task 012 rubric text. Each item has `item_id`, `verdict`, `rationale`, and
`evidence_spans` containing `document_id`, `start_char`, `end_char`. All items must be
present exactly once and have explicit verdicts/rationales. `uncertain` is valid;
null/pending is rejected for this completed diagnostic baseline. Missing unknown
metadata must not be fabricated. Use JSON null for an unknown model.

The tool rebuilds packet/manifest from validated original inputs and checks binding,
complete coverage, response-status compatibility and original span bounds. Full/partial
support references must lie in displayed quotations. Conflict needs distinct opposing
references under the existing validator; semantic correctness remains an AI judgment.

Report version 1 has `review_kind: "ai"`, `status: "ai_review_complete"`, input hashes,
reviewer provenance, overall/by-mode/by-category counts and per-item traces. Original
spans are half-open Unicode codepoint ranges: CRLF is two characters, emoji one.
Each trace contains original text, candidate ranks (one-based) and emitted citation
numbers. Full containment is required; partial overlap does not count. No source text
is normalized. Dynamic content is fenced as inert literal text in Markdown.

`candidate_gap`/`selection_gap` apply to authored support; `ai_evidence_candidate_gap`/
`ai_evidence_selection_gap` apply separately to reviewer references. AI references can
describe opposing positions or context rather than requested-fact support. A candidate
gap is absence from this capture's five candidates, not the corpus. A selection gap
means retrieved but not emitted. `missing_fact_grounded` combines an unsupported AI
verdict, missing-fact category and grounded response. `unresolved_conflict_grounded`
combines a conflicting AI verdict and grounded response. Tags overlap.

## Findings and prioritized handoff

| Mode | Fully supported | Partial | Unsupported | Conflicting |
| --- | ---: | ---: | ---: | ---: |
| Keyword | 10 | 0 | 8 | 6 |
| Semantic | 9 | 1 | 8 | 6 |
| Hybrid | 10 | 0 | 8 | 6 |
| Total | 29 | 1 | 24 | 18 |

All 72 captured answers are grounded quotations, with zero abstentions. AI full-support
rate for this packet is 29/72 (40.3%); it is not representative performance or human
agreement. The report links each recommendation to exact item IDs and original spans:

1. Investigate abstention and unresolved-conflict handling: all eighteen missing-fact
   and eighteen conflict-resolution responses remain grounded. Numbers with different
   units, billing scope or measurement do not establish the requested fact.
2. Investigate candidate recall: multi-05/06 in all modes retrieve only headers,
   omitting both requested retention values. Reranking those five alone cannot recover
   the evidence. A question asking each memo's position can be answered by quoting both.
3. Investigate quotation coverage: semantic multi-04 retrieves PipitDock escalation at
   rank five but omits it; semantic conflict-01 retrieves both opposing retention values
   at ranks three/four but emits only one after two headers. Source inspection confirms
   the selector returns the first three qualifying unique excerpts using overlap OR
   cosine, without requested-fact, coverage or contradiction checks.

Potential abstention, candidate-assembly and coverage improvements are hypotheses,
not tested fixes. Keep successful direct/multi-source cases as controls. Before a
production change, evaluate a concrete alternative with fresh frozen validation and
permission/provenance checks. Task 012 is now observed diagnostic data.

## Verification

The initial new suite failed before the module/review artifacts existed (23 failures).
The completed Task 013 suite has 27 tests. Additional red-to-green checks caught and
fixed canonical-only report prose on another valid bundle, hostile case labels in
recommendation links, and impossible reviewer dates. Offline tests forbid runtime
socket/database connections and reject output inside the input bundle.

Commands executed:

```sh
POSTGRES_PASSWORD=localdev POSTGRES_PORT=55443 \
  docker compose -p bratislava-task013 up -d --wait db
TEST_DATABASE_URL=postgresql+psycopg://pmknowledge:localdev@localhost:55443/pmknowledge_test \
  uv run pytest -q
uv run pytest apps/api/tests/test_support_diagnostics.py apps/api/tests/test_documentation.py -q
uv run ruff check .
uv run ruff format --check .
uv run mypy apps/api/src
DATABASE_URL=postgresql+psycopg://pmknowledge:localdev@localhost:55443/pmknowledge_test \
  uv run alembic check
```

Results: **313 backend tests passed** (24.06s), including all existing source-to-answer,
permission/provenance and controlled-encoder review integration checks. The final
diagnostic/documentation subset passed 31 tests after a source-reference presentation
fix. Ruff lint and formatting checks passed (88 files); mypy passed across twenty
source modules. Alembic reported no upgrade operations. The existing API/database
services, deployment settings, credentials, dependencies and migrations were unchanged.

The README CLI ran successfully into new `.context/` directories. Tests reproduced
both canonical diagnostic files byte-for-byte, checked per-mode totals, preserved
original CRLF/emoji offsets, and confirmed all 72 canonical human verdicts remain null.
The full Task 012 directory has no changes relative to Git. Canonical output hashes:

- `diagnostics.json`: `7b56a796f5ba2b1706ee6ea3c6dee256dac71c7cf50e1da3ae6a07b61e81104b`
- `report.md`: `37800691fa976b484df40dc9f6f0a3912e70470f03f54672c2a581fda9e0db88`

A fresh read-only code reviewer inspected all 72 emitted-quotation lists, distinct
rationales and twelve original documents, checked tracing/attribution, and reproduced
the outputs. No blocking findings were reported. Their minor location-dependent source
link finding was fixed with a repository-relative literal path. They did not run the
full suite or assess human agreement, representative performance, provenance
authenticity or effectiveness of future fixes. The implementing agent ran the checks
above. No frontend behavior changed; browser tests were not needed for this offline CLI.

Stop only the dedicated test service, preserving its volume:

```sh
POSTGRES_PASSWORD=localdev POSTGRES_PORT=55443 docker compose -p bratislava-task013 down
```

## Limitations

- One AI reviewer; no human agreement, blinding, independent semantic validation or
  quality certification. Canonical human findings remain pending.
- The tool validates structures, original references and arithmetic, not the truth
  of AI rationales. Hashes detect inconsistent artifacts, not a malicious operator
  capable of rewriting all inputs, nor authentic model identity or review chronology.
- Offline operator files may contain sensitive data in other uses; authorized local
  access remains necessary. No workspace-authorized export API is added.
- No policy change, tuning, model inference, dependency, migration, new endpoint,
  frontend behavior or automated knowledge promotion. No runtime network/database use.
