import hashlib
from pathlib import PurePath
from uuid import UUID

from fastapi import HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from pmknowledge.chunking import chunk_text
from pmknowledge.embeddings import Embedder, index_version
from pmknowledge.models import DocumentVersion, SourceChunk, SourceDocument, Workspace
from pmknowledge.schemas import IngestRead

MAX_UPLOAD_BYTES = 1024 * 1024


def require_workspace(session: Session, workspace_id: UUID) -> None:
    if session.get(Workspace, workspace_id) is None:
        raise HTTPException(404, "Workspace not found")


def ingest(
    session: Session,
    workspace_id: UUID,
    upload: UploadFile,
    *,
    source_id: UUID | None = None,
    title: str | None = None,
    external_uri: str | None = None,
    embedder: Embedder | None = None,
) -> IngestRead:
    require_workspace(session, workspace_id)
    source = None
    if source_id is not None:
        # Serializes deduplication and numbering for this source, before reading versions.
        source = session.scalar(
            select(SourceDocument)
            .where(SourceDocument.id == source_id, SourceDocument.workspace_id == workspace_id)
            .with_for_update()
        )
        if source is None:
            raise HTTPException(404, "Source not found")
    filename = upload.filename or ""
    if PurePath(filename).suffix.lower() not in {".md", ".markdown", ".txt"}:
        raise HTTPException(415, "Upload a Markdown (.md/.markdown) or plain-text (.txt) file")
    raw = upload.file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File exceeds 1 MiB")
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(422, "File must be valid UTF-8") from exc
    if not content.strip() or "\x00" in content:
        raise HTTPException(422, "File must contain non-empty text without NUL characters")
    sha256 = hashlib.sha256(raw).hexdigest()
    if source is None:
        source = SourceDocument(workspace_id=workspace_id, title=title, external_uri=external_uri)
        session.add(source)
        session.flush()
    version = session.scalar(
        select(DocumentVersion).where(
            DocumentVersion.source_document_id == source.id, DocumentVersion.sha256 == sha256
        )
    )
    duplicate = version is not None
    if version is None:
        previous_number = (
            session.scalar(
                select(func.max(DocumentVersion.version_number)).where(
                    DocumentVersion.source_document_id == source.id
                )
            )
            or 0
        )
        version = DocumentVersion(
            source_document_id=source.id,
            version_number=previous_number + 1,
            sha256=sha256,
            plain_text=content,
        )
        session.add(version)
        session.flush()
        session.add_all(
            [
                SourceChunk(
                    document_version_id=version.id,
                    ordinal=ordinal,
                    text=chunk.text,
                    start_char=chunk.start_char,
                    end_char=chunk.end_char,
                )
                for ordinal, chunk in enumerate(chunk_text(content))
            ]
        )
        session.flush()
    if embedder is not None:
        index_version(session, version.id, embedder)
    chunk_count = (
        session.scalar(
            select(func.count())
            .select_from(SourceChunk)
            .where(SourceChunk.document_version_id == version.id)
        )
        or 0
    )
    return IngestRead(
        workspace_id=workspace_id,
        source_document_id=source.id,
        document_version_id=version.id,
        version_number=version.version_number,
        sha256=version.sha256,
        chunk_count=chunk_count,
        duplicate=duplicate,
    )
