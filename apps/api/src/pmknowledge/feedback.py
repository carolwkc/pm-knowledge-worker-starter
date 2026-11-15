"""Explicitly saved user opinion; not an authoritative query history."""

from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from pmknowledge.access import require_workspace_access
from pmknowledge.auth import Principal
from pmknowledge.models import AnswerFeedback, DocumentVersion, SourceChunk, SourceDocument
from pmknowledge.retrieval import compose_answer
from pmknowledge.schemas import (
    Citation,
    FeedbackCreate,
    FeedbackFilter,
    FeedbackList,
    FeedbackRead,
    FeedbackReceipt,
    FeedbackSummary,
)


def submit_feedback(
    session: Session, workspace_id: UUID, body: FeedbackCreate, *, principal: Principal
) -> tuple[FeedbackReceipt, bool]:
    require_workspace_access(session, workspace_id, principal)
    scope = (
        AnswerFeedback.workspace_id == workspace_id,
        AnswerFeedback.created_by == principal.user_id,
        AnswerFeedback.submission_id == body.submission_id,
    )
    values = body.model_dump(mode="json", exclude={"submission_id"})

    def receipt(record: AnswerFeedback, created: bool) -> tuple[FeedbackReceipt, bool]:
        if any(getattr(record, key) != value for key, value in values.items()):
            raise HTTPException(409, "Submission identifier already used for different feedback")
        return FeedbackReceipt.model_validate(record), created

    existing = session.scalar(select(AnswerFeedback).where(*scope))
    if existing is not None:
        return receipt(existing, False)

    citations: list[Citation] = []
    for index, reported in enumerate(body.answer.sources, 1):
        row = session.execute(
            select(SourceChunk, DocumentVersion, SourceDocument)
            .join(DocumentVersion, DocumentVersion.id == SourceChunk.document_version_id)
            .join(SourceDocument, SourceDocument.id == DocumentVersion.source_document_id)
            .where(
                SourceDocument.workspace_id == workspace_id,
                SourceDocument.id == reported.source_document_id,
                DocumentVersion.id == reported.document_version_id,
                SourceChunk.id == reported.chunk_id,
            )
        ).one_or_none()
        if row is None:
            raise HTTPException(404, "Source evidence not found")
        chunk, version, source = row
        canonical = Citation(
            citation=str(index),
            source_document_id=source.id,
            document_version_id=version.id,
            chunk_id=chunk.id,
            title=source.title,
            external_uri=source.external_uri,
            ordinal=chunk.ordinal,
            excerpt=chunk.text,
            start_char=chunk.start_char,
            end_char=chunk.end_char,
        )
        if canonical.model_dump() != reported.model_dump():
            raise HTTPException(422, "Reported citation does not match stored evidence")
        citations.append(canonical)
    if len({c.chunk_id for c in citations}) != len(citations):
        raise HTTPException(422, "Repeated citation")
    if compose_answer(citations).model_dump() != body.answer.model_dump():
        raise HTTPException(422, "Reported answer does not match quotation format")

    record_id = session.scalar(
        insert(AnswerFeedback)
        .values(
            id=uuid4(),
            workspace_id=workspace_id,
            created_by=principal.user_id,
            submission_id=body.submission_id,
            **values,
        )
        .on_conflict_do_nothing(constraint="uq_feedback_submission")
        .returning(AnswerFeedback.id)
    )
    record = session.scalar(select(AnswerFeedback).where(*scope))
    assert record is not None
    return receipt(record, record_id is not None)


def list_feedback(
    session: Session,
    workspace_id: UUID,
    *,
    principal: Principal,
    rating: FeedbackFilter = "all",
    limit: int = 20,
    offset: int = 0,
) -> FeedbackList:
    require_workspace_access(session, workspace_id, principal, "owner")
    query = select(AnswerFeedback).where(AnswerFeedback.workspace_id == workspace_id)
    if rating != "all":
        query = query.where(AnswerFeedback.rating == rating)
    rows = list(
        session.scalars(
            query.order_by(AnswerFeedback.created_at.desc(), AnswerFeedback.id.desc())
            .offset(offset)
            .limit(limit + 1)
        )
    )
    return FeedbackList(
        feedback=[FeedbackSummary.model_validate(row) for row in rows[:limit]],
        has_more=len(rows) > limit,
    )


def read_feedback(
    session: Session, workspace_id: UUID, feedback_id: UUID, *, principal: Principal
) -> FeedbackRead:
    require_workspace_access(session, workspace_id, principal, "owner")
    record = session.scalar(
        select(AnswerFeedback).where(
            AnswerFeedback.workspace_id == workspace_id,
            AnswerFeedback.id == feedback_id,
        )
    )
    if record is None:
        raise HTTPException(404, "Feedback not found")
    return FeedbackRead.model_validate(record)
