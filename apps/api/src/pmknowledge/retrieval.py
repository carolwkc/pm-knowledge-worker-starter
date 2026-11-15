from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from pmknowledge.documents import require_workspace
from pmknowledge.schemas import AnswerRead, Citation, SearchHit

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
      AND NOT EXISTS (
          SELECT 1 FROM document_version newer
          WHERE newer.source_document_id = d.id AND newer.version_number > v.version_number
      )
      AND c.search_vector @@ query.value
    ORDER BY score DESC, d.id, c.ordinal
    LIMIT :limit
""")


def search(session: Session, workspace_id: UUID, query: str, limit: int) -> list[SearchHit]:
    require_workspace(session, workspace_id)
    rows = session.execute(
        SEARCH_SQL, {"workspace_id": workspace_id, "query": query, "limit": limit}
    ).mappings()
    return [SearchHit.model_validate(row) for row in rows]


def ask(session: Session, workspace_id: UUID, question: str, limit: int) -> AnswerRead:
    hits = search(session, workspace_id, question, limit)[:3]
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
