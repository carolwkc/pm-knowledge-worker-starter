"""CPU-only embeddings. Downloading weights is an explicit CLI operation."""

import argparse
import json
from math import isfinite
from threading import Lock
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import Select, and_, create_engine, exists, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, aliased

from pmknowledge.config import Settings
from pmknowledge.models import (
    ChunkEmbedding,
    DocumentVersion,
    SourceChunk,
    SourceDocument,
    Workspace,
)

if TYPE_CHECKING:
    from fastembed import TextEmbedding

MODEL_ID = "BAAI/bge-small-en-v1.5"
DIMENSIONS = 384


class EmbeddingUnavailable(Exception):
    pass


class Embedder(Protocol):
    model_id: str

    def embed_passages(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, query: str) -> list[float]: ...


class LocalEmbedder:
    model_id = MODEL_ID

    def __init__(self, cache_dir: str) -> None:
        self.cache_dir = cache_dir
        self._model: TextEmbedding | None = None
        self._lock = Lock()

    def _load(self) -> "TextEmbedding":
        from fastembed import TextEmbedding

        with self._lock:
            if self._model is None:
                self._model = TextEmbedding(
                    MODEL_ID,
                    cache_dir=self.cache_dir,
                    local_files_only=True,
                    providers=["CPUExecutionProvider"],
                    threads=2,
                )
        return self._model

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        try:
            return [list(map(float, vector)) for vector in self._load().passage_embed(texts)]
        except Exception as exc:
            raise EmbeddingUnavailable(
                "Local embedding model unavailable; download it first"
            ) from exc

    def embed_query(self, query: str) -> list[float]:
        try:
            return list(map(float, next(iter(self._load().query_embed(query)))))
        except Exception as exc:
            raise EmbeddingUnavailable(
                "Local embedding model unavailable; download it first"
            ) from exc


def index_chunks(session: Session, chunks: list[SourceChunk], embedder: Embedder) -> int:
    inserted = 0
    # Bound inference memory and SQL parameters; the caller owns one transaction.
    for start in range(0, len(chunks), 64):
        batch = chunks[start : start + 64]
        vectors = embedder.embed_passages([chunk.text for chunk in batch])
        if len(vectors) != len(batch) or any(
            len(vector) != DIMENSIONS
            or not all(isfinite(value) for value in vector)
            or not any(vector)
            for vector in vectors
        ):
            raise EmbeddingUnavailable("Embedding model returned invalid vectors")
        statement = (
            insert(ChunkEmbedding)
            .values(
                [
                    {"chunk_id": chunk.id, "model_id": embedder.model_id, "embedding": vector}
                    for chunk, vector in zip(batch, vectors, strict=True)
                ]
            )
            .on_conflict_do_nothing()
            .returning(ChunkEmbedding.chunk_id)
        )
        inserted += len(session.execute(statement).scalars().all())
    return inserted


def unindexed_chunks(model_id: str) -> Select[tuple[SourceChunk]]:
    return (
        select(SourceChunk)
        .outerjoin(
            ChunkEmbedding,
            and_(ChunkEmbedding.chunk_id == SourceChunk.id, ChunkEmbedding.model_id == model_id),
        )
        .where(ChunkEmbedding.chunk_id.is_(None))
    )


def index_version(session: Session, version_id: UUID, embedder: Embedder) -> int:
    chunks = session.scalars(
        unindexed_chunks(embedder.model_id)
        .where(SourceChunk.document_version_id == version_id)
        .order_by(SourceChunk.ordinal)
    ).all()
    return index_chunks(session, list(chunks), embedder)


def backfill_workspace(session: Session, workspace_id: UUID, embedder: Embedder) -> int:
    if session.get(Workspace, workspace_id) is None:
        raise HTTPException(404, "Workspace not found")
    newer = aliased(DocumentVersion)
    chunks = session.scalars(
        unindexed_chunks(embedder.model_id)
        .join(DocumentVersion, DocumentVersion.id == SourceChunk.document_version_id)
        .join(SourceDocument, SourceDocument.id == DocumentVersion.source_document_id)
        .where(
            SourceDocument.workspace_id == workspace_id,
            ~exists().where(
                newer.source_document_id == SourceDocument.id,
                newer.version_number > DocumentVersion.version_number,
            ),
        )
        .order_by(SourceDocument.id, SourceChunk.ordinal)
    ).all()
    return index_chunks(session, list(chunks), embedder)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "download", help="Explicitly download public model weights (no document text)"
    )
    backfill = commands.add_parser(
        "backfill", help="Embed one workspace using cached local weights"
    )
    backfill.add_argument("--workspace-id", type=UUID, required=True)
    args = parser.parse_args()
    settings = Settings()
    if args.command == "download":
        from fastembed import TextEmbedding

        TextEmbedding(
            MODEL_ID,
            cache_dir=settings.embedding_cache_dir,
            providers=["CPUExecutionProvider"],
            threads=2,
        )
        print(json.dumps({"downloaded": MODEL_ID, "cache_dir": settings.embedding_cache_dir}))
        return
    engine = create_engine(settings.database_url, hide_parameters=True)
    try:
        with Session(engine) as session, session.begin():
            count = backfill_workspace(
                session, args.workspace_id, LocalEmbedder(settings.embedding_cache_dir)
            )
        print(json.dumps({"workspace_id": str(args.workspace_id), "embedded_chunks": count}))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
