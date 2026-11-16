# Task 011 — Conservative answer evidence selection

## Outcome

Improve quoted-answer evidence precision and missing-evidence abstention without
introducing a new model or changing search. Permit at most a five percentage-point
evidence-recall decline per mode versus the first-three-hits control.

## Contracts

- `/search` retains its ranking, scores, limits and response schemas. `/ask` uses
  that same bounded candidate list and emits at most three complete original chunks.
- Preserve original text, offsets, source/version identities, workspace permissions,
  latest-version filtering and sequential citation numbering. Keep quotation and
  insufficient-evidence formatting compatible with existing feedback snapshots.
- Query/excerpt lexemes come from PostgreSQL English full-text normalization.
  Lexical coverage is distinct shared query lexemes divided by distinct query lexemes.
  Require positive overlap even when the lexical threshold is zero.
- Keyword candidates qualify lexically; semantic/hybrid candidates qualify lexically
  or through retained raw cosine scores at least the policy and configured floors.
  Fusion and keyword scores must never substitute for cosine. Empty query lexemes
  yield insufficient evidence; unavailable explicit model modes retain their errors.
- Preserve candidate order, deduplicate exact excerpt text, then take up to three.
  No document quota, sentence rewriting, special-case query rules or new dependencies.
- Calibrate each mode only on Task 010: lexical grid 0–1 by 0.05; cosine grid
  0.60–0.90 by 0.025. One pair per mode must satisfy guards at both k=5 and k=10.
  Maximize mean precision, then mean negative answer abstention, then mean evidence
  recall across the two budgets; ties favor lower lexical then cosine thresholds.
- Freeze a separately authored 20-document/40-question validation corpus before
  calibration, and freeze policy constants before inspecting validation results.
  Never retune against held-out results. Preserve Task 002/010 fixtures and artifacts.
- Evaluation version 3 adds `--answer-policy legacy|selected`, paired answers on
  identical captured candidates, raw selection inputs, policy/configuration provenance,
  answer-level positive/negative abstention counts and an operator comparison command.
  Legacy search metrics and integrity/rollback guarantees remain intact.

## Release and verification

At each budget (5 and 10), require strictly improved mean precision and negative
answer abstention across modes, no per-mode regression in either, no recall decline
above five points, 100% citation integrity, and passing isolation/freshness probes.
If any gate fails, retain the legacy production default and report the failed
experiment. A complete benchmark with poor quality is not an integrity failure.

Cover selector boundaries, deduplication, Unicode/CRLF, stopword/single-term questions,
limits, raw cosine versus fusion, permissions before inference, historical evidence,
unchanged search, keyword operation without a model, feedback and CLI compatibility.
Run full backend/documentation/static/migration checks and existing browser flows.
Update the capabilities inventory, roadmap, README and Task 011 verification record.

No new HTTP fields/endpoints, models, migrations, external inference, agent harness,
commits or branch rename. Heuristics do not prove answerability or resolve conflicts.
