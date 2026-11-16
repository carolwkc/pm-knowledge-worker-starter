# Task 010 — Pilot evaluation baseline

## Delivered

The existing rollback-only evaluator now measures a synthetic pilot corpus of twenty
multi-paragraph documents and forty authored questions: ten lexical, ten paraphrase,
ten requiring two sources and ten missing-evidence questions. Gold labels select
exact original Unicode codepoint spans. Distractors include overlapping vocabulary,
conflicting retention statements, untrusted instructions and CRLF/Unicode examples.
This is a baseline of existing behavior, not ranking or threshold tuning.

Specification: [Task 010](../tasks/010-pilot-evaluation.md).
Commands: [README runbook](../README.md#task-010-pilot-evaluation-baseline).
Case-level artifact: [task-010-results.json](evaluations/task-010-results.json).

The CLI adds `--modes` while preserving the original dataset, all-mode and k=3
defaults. Keyword-only execution does not instantiate an encoder. Explicit model
modes use cached weights, with no fallback/download during evaluation. JSON version 2
retains legacy metric fields and adds independent answer checks, evidence counts and
unscored isolation probes. Old datasets have null span-derived metrics. Partially
annotated datasets are rejected to prevent selectively excluding cases from scoring.

The benchmark calls the same ingestion, search and ask services used by HTTP routes.
It audits persisted source/version/chunk identity, metadata, exact original spans,
current version, authenticated membership, citation numbering and complete answer
formatting independently of the production composer. Probe fixtures are separate from
the scored corpus, with 21 foreign documents, historical evidence and denied access
checks for every mode. All fixture rows roll back, including on interrupted runs.
Before scoring, original fixture text, UTF-8 SHA-256 and metadata are compared with
ingestion receipts and persisted versions. Mismatches fail the whole run, even when
unretrieved, and their citations receive no integrity or relevance credit.

## Recorded baseline

Executed offline on 2026-11-16, using Python 3.12.12, FastEmbed 0.9.1,
ONNX Runtime 1.32.0 and the existing `BAAI/bge-small-en-v1.5` CPU encoder.
The public model was explicitly downloaded into `.context/embedding-models` before
the offline run. No document text was sent off-host. PostgreSQL runs in the dedicated
`dubai-task010` Compose project on port 55440 with database `pmknowledge_test`.
Similarity floor: 0.6; retrieval k: 10; maximum answer citations: 3; hybrid candidate
limit: 20 per retriever; RRF k: 60. No existing deployment or `.env` was changed.

Dataset SHA-256:
`773ec783c7daa8f5f77d41f3bb406e4134cc7c18ce145b094341e6659e94d30b`.
The original Task 002 dataset and result artifact are unchanged.

| Mode | Document recall@10 | MRR@10 | Negative abstention | Evidence precision | Evidence recall | Citation integrity |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Keyword | 96.7% | 90.0% | 10.0% | 37.1% (39/105) | 96.7% (29/30) | 100% (105/105) |
| Semantic | 100% | 100% | 30.0% | 45.3% (39/86) | 98.3% (29.5/30) | 100% (86/86) |
| Hybrid | 100% | 91.7% | 10.0% | 36.4% (40/110) | 100% (30/30) | 100% (110/110) |

Document recall/MRR are averaged across thirty positive questions. Document recall
deduplicates expected document IDs within the returned top-k chunks; it does not
collapse the ranking into k distinct documents. Negative abstention is measured on
ten questions and excludes positives. Evidence precision counts verified citations
containing a full labelled support span across **all** questions. Evidence recall is
the average fraction of distinct gold spans covered per positive question; therefore
its numerator may be fractional. Empty denominators are null. These definitions and
case-level counts are necessary to interpret the aggregate scores.

All case integrity checks and isolation/freshness probes passed in all three modes.
The JSON `passed` field and CLI exit 0 describe those checks and run completeness;
they do not mean quality targets were achieved. Poor relevance/abstention remains
visible. Quality thresholds were neither tuned nor introduced.

## Verification

The first unit run had ten expected failures for absent span validation/scoring.
The first integration run had six expected failures for missing mode selection,
answer audits and CLI support. An additional failing configuration test exposed an
uncaught invalid database URL; initialization is now inside the safe error boundary.

Checks run with locked dependencies and the dedicated PostgreSQL test database:

- `uv sync --dev --frozen`.
- `TEST_DATABASE_URL=postgresql+psycopg://pmknowledge:localdev@localhost:55440/pmknowledge_test uv run pytest -q`.
- `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy apps/api/src`.
- Dedicated-database `uv run alembic check`.
- The README's real-model all-mode command with `HF_HUB_OFFLINE=1`, and keyword-only
  execution verified by an integration test that forbids constructing the encoder.

Results: **210 backend tests passed**, including the documentation guard. Ruff lint
and format checks passed; mypy passed across sixteen source files. Alembic reported
no schema drift. The dedicated database contained zero users, workspaces, sources,
versions, chunks and embeddings after verification. No frontend code changed.

Tests cover multiple spans, repeated hits, null denominators, positive abstention,
negative false positives, malformed/partial labels, legacy datasets, forged citation
fields, unsupported added prose, foreign/historical evidence, failed probes, CLI exit
codes/redaction and fixture cleanup on success or ingest/query failures. The full
suite also retains controlled-vector denied-access-before-inference and
pre-ranking/limit-isolation cases. No tests require external inference.

## Independent review

A fresh read-only reviewer independently recomputed all stored case evidence counts
and aggregate metrics against the authored corpus, checked labels and audited the
runner/probes. They identified one P2: persisted text could consistently differ from
the authored fixture and still receive full support credit. Equal-length text
corruption and metadata-corruption tests reproduced that gap (two failing cases).
The original-fixture text/hash/metadata check now rejects both; the full 210-test
suite and static checks pass. The recorded three-mode baseline was regenerated with
the fix and has no fixture failures. Existing UUID ties changed hybrid MRR from the
initial run, as documented; no ranking change was introduced.

The reviewer set aside semantic truth, completeness, contradiction resolution,
pilot readiness and retrieval improvements because these are explicitly outside this
baseline task. These remain documented limitations, not passing quality claims.

## Limitations and operation

- These forty synthetic cases are an authored development benchmark, not a
  statistically representative or held-out pilot cohort. Labels encode expected
  support, not a validated human-judgment study.
- Exact support-span coverage does not establish semantic truth, factual consistency,
  answer completeness or contradiction resolution. Quotes can be valid and irrelevant.
- Embedding revision pinning is unchanged. The report records the model ID and runtime
  versions, not a cryptographic digest of downloaded weights. Existing UUID tie breaks
  can change rankings/MRR across fresh runs; reproducibility means corpus/configuration
  provenance, not byte-identical reports.
- Local operator CLI only: no API/UI/schema/dependency change, feedback mining,
  production instrumentation or external actions. Service evaluation and existing
  HTTP integration tests complement each other; this task adds no browser flow.
- Existing pending caller changes are flushed when SQLAlchemy opens its savepoint;
  evaluation rolls back its own fixtures and does not commit the caller's transaction.

Stop only this task's database, preserving its volume:

```sh
POSTGRES_PASSWORD=localdev POSTGRES_PORT=55440 docker compose -p dubai-task010 down
```

## Evidence-linked failure patterns and next task

The [recorded case-level report](evaluations/task-010-results.json) contains the
rankings, quotations and support counts for these stable case IDs:

- `missing_evidence-01`: keyword/hybrid return boilerplate containing “use” for a
  sourdough question; semantic abstains. Common lexical overlap survives hybrid fusion.
- `missing_evidence-03`: all modes quote Nimbus policy for an unsupported exact price.
  Topic relevance does not mean the requested fact is present.
- `missing_evidence-09`: all modes return retention/recovery statements although no
  source establishes a legal basis resolving Cedar's conflicting policies. Quoting
  both sides cannot establish a resolution.
- `paraphrase-01`: keyword returns inspection-sync evidence rather than the gold
  telemetry statement; semantic retrieves the expected span.
- `multi_source-03`: semantic finds both relevant documents within ten chunks, but
  the top three answer citations cover only one of its two gold spans.

Recommended next task: improve answer evidence selection and missing-evidence
abstention, evaluating any ranking/threshold change against a separately authored
held-out corpus. Preserve these baseline artifacts. Prioritize unsupported-specific-fact
and common-word false positives while monitoring positive evidence recall; do not
optimize document recall alone or label current quotes as verified reasoning.
