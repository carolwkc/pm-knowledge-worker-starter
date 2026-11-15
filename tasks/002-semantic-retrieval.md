# Task 002 — Local semantic retrieval, hybrid ranking and evaluation

## Outcome and boundaries

Add an explicitly enabled local embedding path to the existing evidence API. Support
semantic and hybrid retrieval while preserving workspace isolation, latest-version
selection, verbatim citations and keyword-only operation without model downloads.
No external model calls, frontend, connectors or Task 003 authentication work.

## Implementation plan

1. Use pgvector on PostgreSQL 16 and an Alembic migration for derived chunk embeddings,
   stored separately from original chunks. Use a fixed 384-dimensional BGE small
   English model through FastEmbed on the CPU; model loading at runtime is local-only.
2. Make embeddings opt-in through configuration. Provide an explicit model-download
   command and a workspace-scoped backfill command for previously ingested sources.
   New enabled ingests persist embeddings atomically with source/version/chunk data.
3. Add `mode=keyword|semantic|hybrid` to search and ask, defaulting to keyword for
   compatibility. Semantic retrieval uses exact cosine ranking with a configurable
   minimum similarity (initial default 0.6). Hybrid combines up to 20 candidates from
   each retriever using reciprocal rank fusion (k=60), deduplicates by chunk ID, then
   applies the requested result limit. Scope and latest-version filtering happen in
   both SQL retrievers before candidate selection.
4. Return a safe `503` for explicitly requested semantic/hybrid modes when local
   inference is unavailable; never silently download a model or switch modes. When
   no candidates meet the semantic threshold, return the normal insufficient-evidence
   result. Scores are mode-specific ranking signals, not confidence estimates.
5. Add labelled synthetic paraphrase/relevance cases and a reproducible evaluation
   command reporting recall@k and reciprocal rank for all three modes. Evaluate
   locally using the real model; use controlled vectors in automated database tests
   to verify ranking, isolation, version selection and fusion independently of model
   quality. Evaluation targets are measured on synthetic data only, not pilot claims.
6. Update Compose, setup instructions, contracts and limitations. Run the full suite,
   lint/types, migration checks, and an actual local-model smoke/evaluation pass.

## Acceptance criteria

- Semantic paraphrase queries return cited source spans without sending text off-host.
- Hybrid results include lexical and semantic candidates, contain no duplicate chunks,
  and preserve limits, deterministic ties and workspace boundaries.
- Duplicate uploads/backfills do not duplicate derived embeddings or mutate evidence.
- Superseded versions are excluded in every retrieval mode.
- Keyword mode works with embeddings disabled; missing local models fail explicitly.
- The real-model evaluation records results separately from controlled-vector tests.

## Compatibility and defaults

Existing Task 001 API requests keep keyword behavior. A pgvector-capable PostgreSQL
image replaces the vanilla PostgreSQL image without deleting the PostgreSQL 16 volume.
Existing documents require the explicit workspace backfill before semantic retrieval.
No approximate vector index is needed at this small dataset size. All embeddings
inherit their source's confidentiality; production authorization remains Task 003.
