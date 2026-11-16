# Task 010 — Pilot evaluation baseline

## Outcome

Measure current retrieval and quoted answers on a larger labelled synthetic corpus.
Record keyword, semantic and hybrid results without changing ranking, thresholds or
production behavior. Results guide a subsequent improvement task, not a readiness claim.

## Contracts

- Twenty multi-paragraph documents and forty authored questions: ten lexical, ten
  paraphrase, ten requiring two sources and ten missing-evidence questions. Include
  distractors, conflicting source statements, untrusted instructions, Unicode and CRLF.
- Gold evidence uses document IDs and half-open Unicode codepoint spans. Validate
  unique IDs/spans, nonblank bounded spans and agreement with relevant document IDs.
  Every case has spans (including empty negative labels), or none for legacy datasets.
- Extend the existing evaluator with `--modes`; defaults remain all modes and `--k 3`.
  Pilot runs use `--k 10`. Keyword-only execution never constructs a local model.
  Explicit model modes require cached weights; no download or fallback at runtime.
- Run real ingestion, search and ask services within a rollback-only savepoint. Preserve
  caller-owned unrelated data on both success and failure. Evaluate answers separately
  from retrieval and preserve the three-citation production limit.
- Preserve existing document recall/MRR/abstention fields. Add micro evidence precision,
  macro evidence recall across positive cases, and citation integrity with numerators
  and denominators. Undefined ratios and legacy evidence metrics are null. A citation
  is relevant only when it contains a labelled supporting span, not merely its document.
- Independently audit original source identity, metadata, text, workspace, latest version,
  offsets, citation numbering and complete answer formatting. Record case-level results.
  Verify ingestion text, SHA-256 and metadata against authored fixtures before scoring;
  persisted evidence alone cannot redefine gold support.
- Outside the scored corpus, probe foreign-workspace denial, authorized results with
  21 foreign distractors, and superseded-version exclusion in every selected mode.
- JSON report version 2 includes dataset hash, settings, model and runtime identities.
  Exit 0 means complete measurements and passing integrity probes, regardless of poor
  quality scores; exit 1 means a completed integrity failure; exit 2 means incomplete
  execution or invalid inputs/configuration. Errors omit sensitive exception payloads.

## Acceptance and boundaries

Record an offline all-mode baseline using the real existing encoder. Controlled-vector
tests establish invariants independently of model quality. Cover labels, metrics,
forgery, Unicode/CRLF, permission denial before inference, pre-ranking isolation,
freshness, cleanup and CLI status. Run full backend/static/documentation checks.

Preserve Task 002 fixtures/results. Add no HTTP endpoints, schema migrations,
dependencies, external inference, UI, feedback mining, ranking or threshold changes.
Span relevance does not establish truth, completeness or contradiction resolution.
Fresh fixture UUIDs retain existing tie variability. Do not commit or rename the branch.
