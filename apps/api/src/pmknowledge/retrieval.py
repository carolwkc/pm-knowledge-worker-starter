from math import isfinite
from uuid import UUID

from sqlalchemy import exists, select, text
from sqlalchemy.orm import Session, aliased

from pmknowledge.access import require_workspace_access
from pmknowledge.auth import Principal
from pmknowledge.embeddings import DIMENSIONS, Embedder, EmbeddingUnavailable
from pmknowledge.models import (
    ChunkEmbedding,
    DocumentVersion,
    SourceChunk,
    SourceDocument,
    WorkspaceMembership,
)
from pmknowledge.ranking import reciprocal_rank_fusion
from pmknowledge.schemas import AnswerRead, Citation, RetrievalMode, SearchHit

# All user values are bound parameters. Workspace filtering is part of SQL retrieval,
# before ranking/limiting; no global results are filtered after the fact.
SEARCH_SQL = text("""
    WITH query AS (
        SELECT to_tsquery('english', string_agg(quote_literal(term), ' | ')) AS value
        FROM unnest(tsvector_to_array(to_tsvector('english', :query))) AS term
    )
    SELECT d.id AS source_document_id, v.id AS document_version_id,
           c.id AS chunk_id, d.title, d.external_uri, c.ordinal,
           c.text AS excerpt, c.start_char, c.end_char,
           ts_rank_cd(c.search_vector, query.value, 32) AS score
    FROM source_chunk c
    JOIN document_version v ON v.id = c.document_version_id
    JOIN source_document d ON d.id = v.source_document_id
    CROSS JOIN query
    WHERE d.workspace_id = :workspace_id
      AND EXISTS (
          SELECT 1 FROM workspace_membership m
          WHERE m.workspace_id = d.workspace_id AND m.user_id = :user_id
      )
      AND NOT EXISTS (
          SELECT 1 FROM document_version newer
          WHERE newer.source_document_id = d.id AND newer.version_number > v.version_number
      )
      AND c.search_vector @@ query.value
    ORDER BY score DESC, d.id, c.ordinal
    LIMIT :limit
""")


def keyword_search(
    session: Session, workspace_id: UUID, query: str, limit: int, *, principal: Principal
) -> list[SearchHit]:
    rows = session.execute(
        SEARCH_SQL,
        {
            "workspace_id": workspace_id,
            "user_id": principal.user_id,
            "query": query,
            "limit": limit,
        },
    ).mappings()
    return [SearchHit.model_validate(row) for row in rows]


def semantic_search(
    session: Session,
    workspace_id: UUID,
    query: str,
    limit: int,
    embedder: Embedder,
    min_score: float,
    *,
    principal: Principal,
) -> list[SearchHit]:
    vector = embedder.embed_query(query)
    if len(vector) != DIMENSIONS or not all(isfinite(v) for v in vector) or not any(vector):
        raise EmbeddingUnavailable("Embedding model returned an invalid query vector")
    distance = ChunkEmbedding.embedding.cosine_distance(vector)
    newer = aliased(DocumentVersion)
    statement = (
        select(
            SourceDocument.id.label("source_document_id"),
            DocumentVersion.id.label("document_version_id"),
            SourceChunk.id.label("chunk_id"),
            SourceDocument.title,
            SourceDocument.external_uri,
            SourceChunk.ordinal,
            SourceChunk.text.label("excerpt"),
            SourceChunk.start_char,
            SourceChunk.end_char,
            (1 - distance).label("score"),
        )
        .select_from(SourceChunk)
        .join(ChunkEmbedding, ChunkEmbedding.chunk_id == SourceChunk.id)
        .join(DocumentVersion, DocumentVersion.id == SourceChunk.document_version_id)
        .join(SourceDocument, SourceDocument.id == DocumentVersion.source_document_id)
        .where(
            SourceDocument.workspace_id == workspace_id,
            exists().where(
                WorkspaceMembership.workspace_id == SourceDocument.workspace_id,
                WorkspaceMembership.user_id == principal.user_id,
            ),
            ChunkEmbedding.model_id == embedder.model_id,
            ~exists().where(
                newer.source_document_id == SourceDocument.id,
                newer.version_number > DocumentVersion.version_number,
            ),
            (1 - distance) >= min_score,
        )
        .order_by(distance, SourceDocument.id, SourceChunk.ordinal)
        .limit(limit)
    )
    return [SearchHit.model_validate(row) for row in session.execute(statement).mappings()]


def search(
    session: Session,
    workspace_id: UUID,
    query: str,
    limit: int,
    *,
    principal: Principal,
    mode: RetrievalMode = "keyword",
    embedder: Embedder | None = None,
    min_score: float = 0.6,
) -> list[SearchHit]:
    require_workspace_access(session, workspace_id, principal)
    if mode == "keyword":
        return keyword_search(session, workspace_id, query, limit, principal=principal)
    if embedder is None:
        raise EmbeddingUnavailable("Embeddings disabled")
    candidates = 20 if mode == "hybrid" else limit
    semantic = semantic_search(
        session, workspace_id, query, candidates, embedder, min_score, principal=principal
    )
    if mode == "semantic":
        return semantic
    return reciprocal_rank_fusion(
        keyword_search(session, workspace_id, query, candidates, principal=principal),
        semantic,
        limit,
    )


def ask(
    session: Session,
    workspace_id: UUID,
    question: str,
    limit: int,
    *,
    principal: Principal,
    mode: RetrievalMode = "keyword",
    embedder: Embedder | None = None,
    min_score: float = 0.6,
) -> AnswerRead:
    hits = search(
        session,
        workspace_id,
        question,
        limit,
        principal=principal,
        mode=mode,
        embedder=embedder,
        min_score=min_score,
    )[:3]
    if not hits:
        return AnswerRead(
            answer=(
                "Insufficient evidence: no matching source excerpts were found in this workspace."
            ),
            status="insufficient_evidence",
            sources=[],
        )
    citations = [
        Citation(**hit.model_dump(exclude={"score"}), citation=str(index))
        for index, hit in enumerate(hits, 1)
    ]
    quotes = "\n\n".join(f'[{c.citation}] "{c.excerpt}"' for c in citations)
    return AnswerRead(
        answer=f"Extracted evidence (verbatim source text):\n\n{quotes}",
        status="grounded",
        sources=citations,
    )
