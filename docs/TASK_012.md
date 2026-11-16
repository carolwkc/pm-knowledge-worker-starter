# Task 012 — Human review of requested-fact support

## Delivered

The offline `pmknowledge.support_review` CLI exports immutable source/answer context,
a readable Markdown packet and a separate editable JSON judgment form. It summarizes
explicitly supplied judgments without changing `/ask`, retrieval, thresholds, feedback
or approved knowledge. It adds no HTTP endpoint, migration, dependency or production UI.

Specification: [Task 012](../tasks/012-human-support-review.md).
Start reviewing: [72-item packet](evaluations/task-012-review/packet.md).
Make a local copy of the [blank judgments](evaluations/task-012-review/judgments.json).
**Human findings remain pending: all 72 canonical verdicts are null.** No human ratings
were fabricated or inferred from authored gold labels or automatic metrics.

## Fresh cohort and provenance

The [corpus](../apps/api/evaluation/task012-review.json) contains twelve synthetic
documents and twenty-four questions: six direct support, six multi-source, six missing
specific facts and six unresolved conflict-resolution requests. Positive cases have
original support spans; negative cases have none. Controls include supported prices,
counts/times, unsupported measured facts, topical boilerplate, same-scope conflicting
policies, a question asking for both positions, Unicode/CRLF and hostile source markup.
No original Task 002/010/011 corpus or artifact was changed.

The [freeze](evaluations/task-012-corpus-freeze.json) records SHA-256
`7308d680dc20f235f26fd9d3694d01c0ea17a9a58a1b499cd90790043116f450`.
The corpus was authored and hashed before the first Task 012 capture. No tuning or
new threshold selection occurred. The same authored cohort is now observed evaluation
data, not a fresh held-out set for a later optimization task.

The [capture](evaluations/task-012-review/capture.json) records the real selected-policy
service at k=5 in keyword, semantic and hybrid modes, with the existing
`BAAI/bge-small-en-v1.5` CPU encoder, semantic floor 0.6 and unchanged Task 011 policy.
All fixture, nested case and isolation/freshness checks passed. This establishes
capture consistency/integrity, not requested-fact support or production readiness.
The raw evaluator retains paired legacy diagnostics; the human packet exposes only
the actual selected-policy response and original source content.

The run used Python 3.12.12, FastEmbed 0.9.1, ONNX Runtime 1.32.0 and SQLAlchemy 2.0.57.
Weights were loaded from the existing archived `next-task-plan-v7/embedding-models`
cache with `HF_HUB_OFFLINE=1`; no weights were downloaded or text sent off-host.
The dedicated `maseru-task012` PostgreSQL test database uses port 55442. No existing
deployment, database volume, `.env`, credentials or application settings were changed.

## Run the review workflow without a database or model

From the repository root after `uv sync --dev --frozen`, create your own new bundle:

```sh
uv run python -m pmknowledge.support_review export \
  --cases apps/api/evaluation/task012-review.json \
  --report docs/evaluations/task-012-review/capture.json \
  --output-dir .context/task012-review

cp .context/task012-review/judgments.json .context/task012-my-judgments.json
```

Read `.context/task012-review/packet.md`, including its rubric and full corpus appendix.
Edit only your copied judgment file. Keep all item IDs and manifest binding, set a
stable non-secret `reviewer_id`, and supply a verdict/rationale for each item you review.
Leave unfinished verdicts null. Evidence pointers use this shape (replace values with
actual document IDs and original offsets shown in the packet):

```json
{
  "document_id": "review012-asterline-a",
  "start_char": 0,
  "end_char": 27
}
```

Offsets select half-open Unicode codepoint spans in `cases.json`; count both CR and LF,
and count an emoji as one codepoint. Markdown display may normalize line endings;
the copied original JSON remains the reference. Cite actual supporting/opposing text,
not merely a title. A rationale must explain missing facts or why an abstention is
appropriate; it cannot establish that a fact is absent outside this supplied corpus.

Full/partial support requires references inside displayed quotations. An unresolved
contradiction for the requested scope/time prevents full support even when one side
was omitted by the response. Conflicting judgments require at least two distinct
non-overlapping spans; these may be in one document or in other corpus documents.
Different scopes/times and explicitly resolved statements are not automatically
conflicts. A question asking for both positions can be fully supported by quoting both.
Unjustified abstention requires supporting corpus evidence. The validator checks
references/status compatibility, not whether a human's reasoning is correct.

```sh
uv run python -m pmknowledge.support_review summarize \
  --bundle .context/task012-review \
  --judgments .context/task012-my-judgments.json > .context/task012-human-summary.json
```

Summary JSON version 1 reports overall/mode/category counts, pending/uncertain counts,
reviewer ID, input/judgment hashes and follow-up item IDs. Full-support rate is fully
supported / (fully supported + partially supported + unsupported + conflicting).
Abstentions, uncertain and pending judgments are excluded. Empty denominators are null.
`human_review_pending`, `human_review_incomplete` and `human_review_complete` describe
form completion, never a quality verdict. Uncertain is a submitted judgment but remains
explicit in the counts. There is no pass/fail quality field or automatic promotion.

Both commands exit 0 for valid operations (including blank/partial reviews) and 2 for
invalid inputs or execution failures, with redacted diagnostics. Export refuses an
existing directory. Duplicate JSON keys, nonfinite numbers, changed bundle contents,
incorrect settings, missing/duplicate/unknown item IDs, invalid spans, missing rationales
and incompatible verdicts fail. Reproductions must use new directories under `.context/`.

## Reproduce the real capture

Keep the canonical bundle and frozen corpus intact. Use an existing cached model and
dedicated migrated test database; no runtime downloads or silent mode fallback occur:

```sh
POSTGRES_PASSWORD=localdev POSTGRES_PORT=55442 \
  docker compose -p maseru-task012 up -d --wait db
export DATABASE_URL=postgresql+psycopg://pmknowledge:localdev@localhost:55442/pmknowledge_test
uv run alembic upgrade head
export EMBEDDING_CACHE_DIR=.context/embedding-models
export HF_HUB_OFFLINE=1

uv run python -m pmknowledge.evaluation \
  --cases apps/api/evaluation/task012-review.json --k 5 --answer-policy selected \
  > .context/task012-recapture.json
uv run python -m pmknowledge.support_review export \
  --cases apps/api/evaluation/task012-review.json \
  --report .context/task012-recapture.json --output-dir .context/task012-recapture-review
```

Point `EMBEDDING_CACHE_DIR` at your actual existing cache before running. Evaluation
uses real ingestion/search/ask and rolls back fixtures; fixture UUID ties may change
rankings, capture hashes and item IDs across new runs. Do not attach old judgments to
a new run. Export and summary themselves require neither database nor inference.

## Verification

The pre-change backend baseline passed 247 tests. Before implementation, the new
workflow tests failed with the missing module/corpus (12 failures and 20 setup errors).
The canonical artifact acceptance test also failed before export. After implementation
and export, all **39 Task 012 tests passed**, including the controlled-encoder integration
flow, fixture rollback, corpus freeze, blank/partial summaries, pointer containment,
omitted-source conflicts, abstentions, malformed/tampered input and inert Markdown.

Commands run against the dedicated test database:

```sh
TEST_DATABASE_URL=postgresql+psycopg://pmknowledge:localdev@localhost:55442/pmknowledge_test \
  uv run pytest -q
uv run pytest apps/api/tests/test_documentation.py -q
uv run ruff check .
uv run ruff format --check .
uv run mypy apps/api/src
DATABASE_URL=postgresql+psycopg://pmknowledge:localdev@localhost:55442/pmknowledge_test \
  uv run alembic check
```

Results: **286 backend tests passed** (22.12s); the explicit documentation guard passed
all four tests. Ruff lint and format checks passed (83 files); mypy passed across
nineteen source modules; Alembic reported no drift. All twelve application tables were
empty after fixture cleanup. The README export and blank-summary commands also ran
successfully under `.context/`, reproducing 72 pending items and null support rates.
The recorded real-model capture passed all mode/case/fixture/isolation checks.

## Independent review

A fresh read-only reviewer found no Critical, Important or Minor findings. They
independently reproduced all five canonical bundle files byte-for-byte, checked
every emitted quotation against original spans (including Unicode/CRLF), confirmed
72 pending judgments and exercised corrupted response/excerpt/coverage/document
bindings and all-verdict summary arithmetic. They found no production behavior change.

They did not judge human semantic verdicts (none exist), freeze chronology or model
weight authenticity; these remain explicit limits rather than passing claims. They
relied on the existing evaluator for database-backed provenance/isolation and did not
repeat the implementing agent's real-model/database/full-suite checks. Markdown fence
construction and hostile fixtures were inspected; no Markdown renderer or browser
was exercised. Human review and renderer behavior remain distinct from capture and
reference integrity. Verification results above were executed by the implementing agent.

## Limitations and follow-up

- Review-ready materials are delivered; human findings and any subsequent tuning are
  separate work. This is synthetic authored data, not blinded/representative research.
- One reviewer per form. No agreement metric, adjudication, annotations UI or release
  gate. A complete form may contain uncertainty or poor-quality judgments.
- Gold labels remain available in copied corpus/raw reports for provenance; the packet
  omits them, but there is no blinding or access-control claim for this operator bundle.
- Source files and review data can contain sensitive text in other uses. This task's
  canonical artifacts contain synthetic content only. The commands are operator tools,
  not a workspace-authorized export API, and must not bypass source access permissions.
- Hashes and deterministic reconstruction detect inconsistent artifacts; they do not
  authenticate an operator who can rewrite all inputs, prove freeze chronology or
  cryptographically pin model weights. Offline checks do not replace the evaluator's
  database-backed permission/provenance audits.
- Source markup and URI metadata remain inert. Human comments are data, not commands.
  Original text is not rewritten. No reviewed judgment changes authoritative knowledge.
- No production or frontend code changed; source/evaluation compatibility remains
  covered by the backend suite. Browser tests are outside this offline tooling change.

Stop only the dedicated service, preserving its volume:

```sh
POSTGRES_PASSWORD=localdev POSTGRES_PORT=55442 docker compose -p maseru-task012 down
```
