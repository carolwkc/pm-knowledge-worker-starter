from uuid import UUID

from pmknowledge.ranking import reciprocal_rank_fusion
from pmknowledge.schemas import SearchHit


def hit(number):
    return SearchHit(
        source_document_id=UUID(int=number),
        document_version_id=UUID(int=100 + number),
        chunk_id=UUID(int=200 + number),
        title="Synthetic",
        external_uri=None,
        ordinal=0,
        excerpt="Evidence.",
        start_char=0,
        end_char=9,
        score=0.9,
    )


def test_shared_evidence_ranks_first_without_duplicate_citations():
    first, second, third = hit(1), hit(2), hit(3)
    results = reciprocal_rank_fusion([first, second], [third, second], limit=3)
    assert [item.chunk_id for item in results] == [second.chunk_id, first.chunk_id, third.chunk_id]
    assert results[0].score > results[1].score
    assert len(results) == 3
    # Input scores describe the underlying retriever and must not be mutated.
    assert second.score == 0.9


def test_fusion_honors_limit_and_handles_one_empty_retriever():
    first, second = hit(1), hit(2)
    assert reciprocal_rank_fusion([], [first, second], limit=1)[0].chunk_id == first.chunk_id
    assert reciprocal_rank_fusion([], [], limit=5) == []
