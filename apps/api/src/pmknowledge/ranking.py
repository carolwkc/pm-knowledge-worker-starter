from pmknowledge.schemas import SearchHit


def reciprocal_rank_fusion(
    keyword: list[SearchHit], semantic: list[SearchHit], limit: int
) -> list[SearchHit]:
    hits = {}
    scores: dict[str, float] = {}
    for ranked in (keyword, semantic):
        for rank, hit in enumerate(ranked, 1):
            key = str(hit.chunk_id)
            hits[key] = hit
            scores[key] = scores.get(key, 0.0) + 1 / (60 + rank)
    merged = [hit.model_copy(update={"score": scores[key]}) for key, hit in hits.items()]
    return sorted(merged, key=lambda hit: (-hit.score, str(hit.source_document_id), hit.ordinal))[
        :limit
    ]
