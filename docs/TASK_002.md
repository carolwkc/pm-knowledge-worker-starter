# Task 002: local semantic retrieval, hybrid ranking and evaluation

## Delivered slice

- Opt-in CPU embeddings with FastEmbed 0.9.1 and the fixed 384-dimensional
  `BAAI/bge-small-en-v1.5` English encoder. Model download is an explicit CLI action;
  runtime loading only uses local files. There are no external model API calls.
- Alembic migration `0002` enables pgvector and creates a separate derived table
  keyed by chunk/model. The PostgreSQL 16 data volume and original evidence are kept.
- Search/ask accept `keyword`, `semantic`, and `hybrid` modes. Keyword stays the
  default. Both SQL retrievers scope by workspace and current version before ranking.
- Exact cosine search gates candidates at similarity 0.6 by default. Hybrid merges
  20 candidates per retriever using RRF with k=60, deduplicates, and applies the limit.
- Enabled uploads embed atomically. Workspace-scoped backfill skips indexed pairs;
  inference/inserts use batches of 64 under one transaction. Failure rolls back all
  writes. Unavailable models return a safe 503; modes never silently change.
- A labelled synthetic evaluation runs the real local encoder and SQL retrieval,
  then rolls back its temporary workspace. The report includes model/package identity,
  dataset SHA-256, individual cases, positive metrics and negative-case abstention.

Setup and curl examples are in [README](../README.md#task-002-enable-local-semantic-and-hybrid-retrieval).
The implementation plan is [Task 002](../tasks/002-semantic-retrieval.md).

## Verification

Executed with Python 3.12, PostgreSQL 16 with pgvector 0.8.1, and cached public model
weights on the local Mac and in the Linux arm64 API container. No real company data
was used. The normal test suite uses controlled vectors to exercise SQL/ranking
invariants; those tests make no claims about model quality.

| Command / scenario | Outcome |
| --- | --- |
| `uv sync --dev --frozen` | Locked CPU/vector dependencies installed |
| `uv run pytest -q` | 66 passed; no skips or warnings |
| `uv run ruff check .` / `uv run ruff format --check .` | Passed |
| `uv run mypy apps/api/src` | Passed, 11 modules |
| `uv run alembic upgrade head` / `uv run alembic check` | Migration applied; no schema drift |
| `docker compose up -d --build --wait` | Both services healthy; existing data preserved |
| Explicit Docker model download | Public weights cached in the persistent volume |
| Existing fixture workspace backfill, repeated | 8 chunks inserted; second run inserted 0 |
| Real HTTP semantic and hybrid Q&A | Paraphrase returned the relevant exact quote and citation |
| Docker evaluation with `HF_HUB_OFFLINE=1` | Completed using cached weights; fixture data rolled back |

Tests cover mode validation, model disable/failure behavior, original source rollback,
finite/nonzero vector validation, cosine thresholds, wrong-model exclusion, cross-workspace
isolation, current-version filtering, hybrid fusion/dedup/limits, backfill idempotency,
multi-batch failure rollback, evaluation metrics, gold-label validation and data cleanup.
The missing API wiring, missing evaluation module and batch interruption test were
observed failing before the corresponding implementations passed. Final review was
an author self-review because no subagent tool was available.

## Recorded synthetic results

Dataset: 8 short synthetic documents, 8 positive questions, 2 unrelated questions.
Settings: top 3, similarity floor 0.6. Full case-level output is in
[task-002-results.json](evaluations/task-002-results.json).

| Mode | Recall@3 (positive cases) | MRR@3 (positive cases) | No-evidence accuracy (negative cases) |
| --- | ---: | ---: | ---: |
| Keyword | 37.5% | 37.5% | 50% |
| Semantic | 87.5% | 87.5% | 100% |
| Hybrid | 100% | 87.5% | 50% |

The cosine threshold missed the offline-workflow paraphrase, which keyword search
recovered in hybrid mode. Hybrid also retained a weak lexical match between a cooking
question and an authentication document (the word “use”), so it failed to abstain.
RRF ties use source UUIDs; MRR may vary across freshly created evaluation workspaces.
These tiny synthetic results do not establish pilot recall, groundedness, safety,
or production readiness. No threshold was tuned to make these cases all pass.

## Limitations and next review

- Client-provided workspace IDs still do not authenticate or authorize callers.
  This remains a local synthetic-data scaffold; Task 003 has not started.
- A matching quote is not a verified answer. Scores are ranking signals rather than
  confidence; hybrid can include irrelevant lexical hits, and contradictions are not
  detected. Broader held-out evaluation and threshold calibration remain necessary.
- Existing sources need explicit backfill. Without it, semantic coverage is incomplete;
  hybrid can still retrieve unindexed chunks lexically. Exact vector search and the
  backfill selection are intended for small corpora, not a production-scale index.
- Backfill loads missing chunk metadata into memory and holds one transaction while
  inference runs. Batches bound vector/SQL size, but resumable streaming is deferred.
- The encoder is English-only with a 512-token input limit. Character-based chunks
  can exceed that token budget for some inputs. Model name and Python dependencies
  are fixed; stronger model-weight revision pinning remains future work.
- No frontend, external connectors, generative LLM, agent orchestration or external
  write actions were introduced. Review this slice before starting the next task.
