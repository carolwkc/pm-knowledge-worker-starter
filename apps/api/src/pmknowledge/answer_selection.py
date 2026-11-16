"""Bounded quotation selection; relevance heuristics are not answerability proofs."""

from collections.abc import Mapping, Set
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from pmknowledge.schemas import RetrievalMode, SearchHit

AnswerPolicy = Literal["legacy", "selected"]
DEFAULT_ANSWER_POLICY: AnswerPolicy = "selected"  # Task 011 held-out gates passed at k=5 and k=10
POLICY_ID = "lexical-cosine-selection-v1"


@dataclass(frozen=True)
class Thresholds:
    lexical: float
    cosine: float | None


# Frozen on Task 010 development captures at k=5 and k=10, before validation.
# Provenance and the bounded grid search: docs/evaluations/task-011-policy.json.
THRESHOLDS: dict[RetrievalMode, Thresholds] = {
    "keyword": Thresholds(0.0, None),
    "semantic": Thresholds(0.3, 0.65),
    "hybrid": Thresholds(0.8, 0.65),
}


def english_lexemes(session: Session, texts: list[str]) -> list[set[str]]:
    """One bound, ordered batch. Original evidence is never normalized or rewritten."""
    rows = session.scalars(
        text("""
            SELECT tsvector_to_array(to_tsvector('english', input.value))
            FROM unnest(CAST(:texts AS text[])) WITH ORDINALITY AS input(value, n)
            ORDER BY input.n
        """),
        {"texts": texts},
    )
    return [set(row) for row in rows]


def select_evidence(
    hits: list[SearchHit],
    question_lexemes: Set[str],
    excerpt_lexemes: Mapping[UUID, Set[str]],
    cosine_scores: Mapping[UUID, float],
    mode: RetrievalMode,
    min_score: float,
    thresholds: Thresholds,
) -> list[SearchHit]:
    if not question_lexemes:
        return []
    selected: list[SearchHit] = []
    seen: set[str] = set()
    for hit in hits:
        coverage = len(question_lexemes & excerpt_lexemes[hit.chunk_id]) / len(question_lexemes)
        lexical = coverage > 0 and coverage >= thresholds.lexical
        cosine = cosine_scores.get(hit.chunk_id)
        semantic = (
            mode != "keyword"
            and thresholds.cosine is not None
            and cosine is not None
            and cosine >= max(min_score, thresholds.cosine)
        )
        if (lexical or semantic) and hit.excerpt not in seen:
            selected.append(hit)
            seen.add(hit.excerpt)
            if len(selected) == 3:
                break
    return selected
