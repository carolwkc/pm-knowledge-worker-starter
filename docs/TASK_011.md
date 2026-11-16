# Task 011 — Conservative answer evidence selection

## Delivered

`/ask` now uses `lexical-cosine-selection-v1`, after held-out release gates passed
at both k=5 and k=10. The pure selector preserves ranking order and original chunks,
deduplicates exact excerpt strings and emits at most three quotations. It requires
positive lexical overlap or, in semantic/hybrid mode, sufficient raw cosine. It does
not compare fusion scores with cosine thresholds. Search and HTTP schemas are unchanged.

PostgreSQL English lexemes are computed in one ordered bound batch after authorized
retrieval. Stopword-only questions abstain. Keyword requests never construct an
encoder. Explicit unavailable model modes still fail rather than silently falling back.
The service retains raw cosine from its existing retrieval pass without extra query
inference. Formatting and feedback validation remain compatible with old snapshots;
feedback does not rerun the new relevance policy against a historical answer.

Specification: [Task 011](../tasks/011-answer-evidence-selection.md).

## Freeze and calibration

The separately authored validation corpus contains 20 documents and 40 questions,
ten each lexical, paraphrase, multiple-source and missing-evidence. It uses different
products/statements from Task 010, with exact support spans, repeated boilerplate,
unsupported facts, conflicting policies, Unicode/CRLF and untrusted source instructions.
It was authored and hashed before calibration. Its SHA-256 is
`76c75a7251abd05c1893dc2cb1fc6643a9d92e0834d5a0d87a0f6339baaeb177`.
The [corpus freeze](evaluations/task-011-validation-freeze.json) records the file.

Calibration used only the unchanged Task 010 corpus. Candidate captures at
[k=5](evaluations/task-011-development-k5.json) and
[k=10](evaluations/task-011-development-k10.json) preserve complete inputs and the
development-time policy configuration. Their primary answers use the legacy policy;
their provisional selected arms are not the final calibrated policy. The
[policy freeze](evaluations/task-011-policy.json) records source capture hashes,
the chosen constants and their replayed development metrics.

The bounded grid used lexical thresholds 0–1 by 0.05 and cosine thresholds 0.60–0.90
by 0.025. Each mode's pair had to preserve precision/negative answer abstention and
lose no more than five evidence-recall points at **both** budgets. We maximized mean
precision, then abstention, then recall across budgets; ties favored lower thresholds.
This single pair per mode avoids selecting a policy for only one candidate budget.

| Mode | Lexical coverage floor | Raw cosine alternative |
| --- | ---: | ---: |
| Keyword | 0, with strictly positive overlap required | none |
| Semantic | 0.30 | 0.65 |
| Hybrid | 0.80 | 0.65 |

The cosine alternative also respects the runtime semantic floor. An empty query
lexeme set never qualifies. These constants and policy artifact were frozen before
validation; no held-out tuning occurred. The development freeze artifact SHA-256 is
`d3204ca573b23b4a2a36879b6c7b5744bbe6bc77c4eda6adda37f267670f09cb`.

## Held-out results

Executed offline using cached existing `BAAI/bge-small-en-v1.5` weights, Python
3.12.12, FastEmbed 0.9.1, ONNX Runtime 1.32.0 and SQLAlchemy 2.0.57. No model was
downloaded or document text sent off-host. The cache used for this run was the
existing Conductor archived context `next-task-plan-v7/embedding-models`.
The dedicated `tegucigalpa-task011` PostgreSQL test database used port 55441;
the browser API used port 58011. No existing deployment or `.env` was changed.

| k | Mode | Precision: legacy → selected | Evidence recall: legacy → selected | Negative answer abstention: legacy → selected |
| --- | --- | ---: | ---: | ---: |
| 5 | Keyword | 31.6% → 32.5% | 91.7% → 91.7% | 10% → 10% |
| 5 | Semantic | 36.7% → 47.1% | 100% → 100% | 20% → 20% |
| 5 | Hybrid | 34.2% → 49.4% | 100% → 100% | 10% → 40% |
| 10 | Keyword | 32.5% → 33.0% | 95% → 95% | 10% → 10% |
| 10 | Semantic | 36.7% → 47.1% | 100% → 100% | 20% → 20% |
| 10 | Hybrid | 34.2% → 48.8% | 100% → 100% | 10% → 40% |

At each budget, mean precision and negative answer abstention across modes strictly
improved; neither regressed in any mode, and evidence recall did not decline.
Citation integrity was 100% in all modes/arms; workspace and freshness probes passed.
Positive answer abstention was zero in every mode/arm. The denominator for negative
abstention is ten questions per mode. Evidence recall remains the macro fraction of
gold spans per positive question; it is not the percentage of answered questions.

Case-level paired evidence, original labels and diagnostic selection inputs are in
the validation captures at [k=5](evaluations/task-011-validation-k5.json) and
[k=10](evaluations/task-011-validation-k10.json). Both policies use exactly the same
captured candidate list; independent audits cover both arms, and the real ask service
must match its captured-policy replay. The
[release gate](evaluations/task-011-release-gate.json) records both budget checks
and capture hashes. Its success permitted the explicit production-default change;
the CLI never promotes a policy automatically.

## Reproduction

Use a dedicated migrated test database and already cached model weights. Keep fixed
artifacts above intact; write new runs under `.context/`. Fresh fixture UUID ties
may change rankings; paired comparisons within each run retain identical candidates.

```sh
POSTGRES_PASSWORD=localdev POSTGRES_PORT=55441 \
  docker compose -p tegucigalpa-task011 up -d --wait db
DATABASE_URL=postgresql+psycopg://pmknowledge:localdev@localhost:55441/pmknowledge_test \
  uv run alembic upgrade head

# Point this at an existing local model cache; no download occurs.
export EMBEDDING_CACHE_DIR=.context/embedding-models
export HF_HUB_OFFLINE=1
export DATABASE_URL=postgresql+psycopg://pmknowledge:localdev@localhost:55441/pmknowledge_test
mkdir -p .context
for k in 5 10; do
  uv run python -m pmknowledge.evaluation \
    --cases apps/api/evaluation/task011-validation.json --k "$k" \
    --answer-policy selected > ".context/task011-validation-k${k}.json"
done
uv run python -m pmknowledge.selection_benchmark validate \
  --cases apps/api/evaluation/task011-validation.json \
  --reports .context/task011-validation-k5.json .context/task011-validation-k10.json

# Recompute the development choice from the recorded development captures only.
uv run python -m pmknowledge.selection_benchmark calibrate \
  --cases apps/api/evaluation/pilot-cases.json \
  --reports docs/evaluations/task-011-development-k5.json \
            docs/evaluations/task-011-development-k10.json > .context/task011-policy-replay.json
```

Evaluation defaults remain Task 002 cases, all modes and k=3, with the selected answer
policy now default. `--answer-policy legacy` explicitly runs the former behavior.
`--modes keyword` requires no model. Report version 3 retains old metric fields and
adds paired policy metrics, configuration, raw selection inputs, dataset hash and
answer-level positive/negative abstention with counts. Ratios without denominators
remain null. Evaluation exit 0 still means complete measurements and passing integrity
checks, not passing quality gates; 1 means integrity failure; 2 means incomplete input,
configuration or execution. The separate validator exits 0 for passing quality gates,
1 for completed failed gates and 2 for invalid/incomplete captures. Errors are redacted.

## Verification

The 210-test pre-change backend baseline passed. New tests were observed failing
before their implementations: six selector failures, four evaluation contract failures,
six missing benchmark failures, a nonfinite gate-input failure, the frozen-threshold
mismatch and the HTTP default's duplicate quotation behavior. Targeted checks passed
after the corresponding changes.

Backend commands use `TEST_DATABASE_URL` above: `uv run pytest -q`,
`uv run pytest apps/api/tests/test_documentation.py -q`, `uv run ruff check .`,
`uv run ruff format --check .`, `uv run mypy apps/api/src` and test-database
`uv run alembic check`. Browser verification uses the existing E2E Compose override
and `E2E_DATABASE_URL`/`E2E_BASE_URL` above with `npm --prefix apps/web run test:e2e`.
Results: **247 backend tests passed**, including the explicit four-test documentation
guard; Ruff lint/format and strict mypy passed across eighteen source files; Alembic
reported no drift. Web type/lint/format/build checks and **135 web unit tests passed**.
The existing **eleven browser flows passed**, including Q&A, feedback, historical
citations, access loss, uploads and owner review. All twelve application tables in
the dedicated test database were empty after fixture cleanup.

## Independent review

A fresh read-only reviewer independently replayed all four captures, checking
original source spans, paired answers, metrics, artifact hashes and both release
gates. They found no production selection, permission or feedback compatibility
issue. They identified one P2 in the operator validator: it trusted top-level success
enough to accept empty case lists or failed nested probes with unchanged aggregates.

Nine corruption variants reproduced that finding before the fix. Capture checking
now requires exact unique dataset coverage, consistent fixture/mode/probe/case
success, matching original fixture text/metadata, matching paired/service answers,
and recomputed evidence counts and policy metrics. All nine tests then passed, as
did the full 247-test backend suite. The hardened validator reproduced the original
release-gate artifact exactly. The policy, validation corpus and recorded captures
were preserved; no threshold was retuned.

The reviewer did not independently judge freeze chronology, statistical
generalizability or fresh model/database/browser execution. Chronology is recorded
in the ordered implementation session and `.context` ledger; runtime checks above
were executed by the implementing agent. No blinded replication or generalization
claim is made. Offline capture consistency checking does not authenticate arbitrary
operator JSON or replace the evaluator's database-backed permission/provenance audit.

## Limitations and follow-up

- These authored synthetic cohorts are small, not statistically representative or
  independently blinded pilot research. The same implementer authored the validation
  corpus before calibration; its results were withheld until the policy was frozen.
- Keyword abstention remained 10%, and semantic abstention remained 20% on validation.
  Unsupported exact-price (`missing_evidence-01`), measured-percentage (`-02`) and
  conflict-resolution (`-07`) requests can still receive topical quotations. Hybrid
  also still fails six of the ten negative cases. No truth/readiness claim follows.
- Deduplication is exact string equality, not semantic similarity. Selecting one copy
  can omit independent corroborating identities. Whole chunks can include irrelevant
  surrounding prose. There is no per-document quota or requested-fact recognizer.
- Thresholds are English/synthetic-corpus heuristics; different configured semantic
  floors and model revisions were not calibrated. Stored fixture UUID ties can vary
  across fresh runs. Search and candidate generation are not tuned here.
- Original evidence, feedback, migrations, dependencies and HTTP interfaces remain
  unchanged. No external actions, new model, feedback mining or agent harness exists.
- Next work should use new validation data and human judgment of requested-fact
  support; do not tune again on this now-observed validation corpus.

Stop only this task's services, preserving volumes:

```sh
POSTGRES_PASSWORD=localdev POSTGRES_PORT=55441 API_PORT=58011 \
  docker compose -p tegucigalpa-task011 -f compose.yaml -f apps/web/e2e/compose.yaml down
```
