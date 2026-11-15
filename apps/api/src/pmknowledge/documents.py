import hashlib
from pathlib import PurePath
from uuid import UUID

from fastapi import HTTPException, UploadFile
from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session, aliased

from pmknowledge.access import require_workspace_access
from pmknowledge.auth import Principal
from pmknowledge.chunking import chunk_text
from pmknowledge.embeddings import Embedder, index_version
from pmknowledge.models import DocumentVersion, SourceChunk, SourceDocument, WorkspaceMembership
from pmknowledge.schemas import IngestRead, SourceVersionRead

MAX_UPLOAD_BYTES = 1024 * 1024


def read_source_version(
    session: Session,
    workspace_id: UUID,
    source_id: UUID,
    version_id: UUID,
    *,
    principal: Principal,
) -> SourceVersionRead:
    require_workspace_access(session, workspace_id, principal)
    newer = aliased(DocumentVersion)
    row = (
        session.execute(
            select(
                SourceDocument.workspace_id,
                SourceDocument.id.label("source_document_id"),
                DocumentVersion.id.label("document_version_id"),
                SourceDocument.title,
                SourceDocument.external_uri,
                DocumentVersion.version_number,
                DocumentVersion.sha256,
                DocumentVersion.ingested_at,
                DocumentVersion.plain_text,
                (
                    ~exists().where(
                        newer.source_document_id == SourceDocument.id,
                        newer.version_number > DocumentVersion.version_number,
                    )
                ).label("source_is_latest"),
            )
            .join(DocumentVersion, DocumentVersion.source_document_id == SourceDocument.id)
            .where(
                SourceDocument.workspace_id == workspace_id,
                SourceDocument.id == source_id,
                DocumentVersion.id == version_id,
                exists().where(
                    WorkspaceMembership.workspace_id == SourceDocument.workspace_id,
                    WorkspaceMembership.user_id == principal.user_id,
                ),
            )
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(404, "Source version not found")
    return SourceVersionRead.model_validate(row)


def ingest(
    session: Session,
    workspace_id: UUID,
    upload: UploadFile,
    *,
    principal: Principal,
    source_id: UUID | None = None,
    title: str | None = None,
    external_uri: str | None = None,
    embedder: Embedder | None = None,
) -> IngestRead:
    require_workspace_access(session, workspace_id, principal, "editor")
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
