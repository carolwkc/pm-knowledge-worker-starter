"""Explicit extractive proposals and human-reviewed decisions; no model or source instructions."""

import re
from typing import cast
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import Select, exists, select
from sqlalchemy.orm import Session, aliased

from pmknowledge.access import lock_owned_workspace, require_workspace_access
from pmknowledge.auth import Principal
from pmknowledge.models import (
    ApprovedDecision,
    DocumentVersion,
    KnowledgeProposal,
    ReviewEvent,
    SourceChunk,
    SourceDocument,
    Workspace,
)
from pmknowledge.schemas import (
    DecisionRead,
    Evidence,
    ExtractionRead,
    ProposalFilter,
    ProposalRead,
    ProposalStatus,
    ReviewRead,
    ReviewWrite,
)

EXTRACTOR_VERSION = "decision-marker-v1"
DECISION_MARKER = re.compile(
    r"^(?:\#{1,6}[ \t]+)?(?:Decision:|We[ \t]+(?:decided|prioritised|prioritized)\b)\s*\S",
    re.IGNORECASE,
)


def is_decision_chunk(statement: str) -> bool:
    return DECISION_MARKER.match(statement) is not None


def _proposal_query(
    workspace_id: UUID,
) -> Select[
    tuple[
        KnowledgeProposal,
        SourceChunk,
        DocumentVersion,
        SourceDocument,
        ReviewEvent,
        ApprovedDecision,
    ]
]:
    return (
        select(
            KnowledgeProposal,
            SourceChunk,
            DocumentVersion,
            SourceDocument,
            ReviewEvent,
            ApprovedDecision,
        )
        .join(SourceChunk, SourceChunk.id == KnowledgeProposal.chunk_id)
        .join(DocumentVersion, DocumentVersion.id == SourceChunk.document_version_id)
        .join(SourceDocument, SourceDocument.id == DocumentVersion.source_document_id)
        .outerjoin(ReviewEvent, ReviewEvent.proposal_id == KnowledgeProposal.id)
        .outerjoin(
            ApprovedDecision,
            (ApprovedDecision.proposal_id == KnowledgeProposal.id)
            & (ApprovedDecision.workspace_id == workspace_id),
        )
        .where(
            KnowledgeProposal.workspace_id == workspace_id,
            SourceDocument.workspace_id == workspace_id,
        )
        .execution_options(populate_existing=True)
    )


def _evidence(chunk: SourceChunk, version: DocumentVersion, source: SourceDocument) -> Evidence:
    return Evidence(
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


def _proposal_read(
    proposal: KnowledgeProposal,
    chunk: SourceChunk,
    version: DocumentVersion,
    source: SourceDocument,
    event: ReviewEvent | None,
    decision: ApprovedDecision | None,
) -> ProposalRead:
    return ProposalRead(
        id=proposal.id,
        workspace_id=proposal.workspace_id,
        statement=proposal.statement,
        evidence=_evidence(chunk, version, source),
        extractor_version=proposal.extractor_version,
        created_by=proposal.created_by,
        created_at=proposal.created_at,
        status=cast(ProposalStatus, proposal.status),
        review=ReviewRead.model_validate(event) if event is not None else None,
        decision_id=decision.id if decision is not None else None,
    )


def _require_latest(session: Session, source_id: UUID, version: DocumentVersion) -> None:
    newer = session.scalar(
        select(DocumentVersion.id)
        .where(
            DocumentVersion.source_document_id == source_id,
            DocumentVersion.version_number > version.version_number,
        )
        .limit(1)
    )
    if newer is not None:
        raise HTTPException(
            409, "Source has a newer version; extract proposals from the latest version"
        )


def generate_proposals(
    session: Session, workspace_id: UUID, source_id: UUID, version_id: UUID, *, principal: Principal
) -> ExtractionRead:
    require_workspace_access(session, workspace_id, principal, "editor")
    # Acquire the workspace FK's key-share lock before the source update lock.
    # Review/membership writers lock workspace first; reversing it can deadlock.
    session.execute(
        select(Workspace.id)
        .where(Workspace.id == workspace_id)
        .with_for_update(read=True, key_share=True)
    )
    require_workspace_access(session, workspace_id, principal, "editor")
    source = session.scalar(
        select(SourceDocument)
        .where(
            SourceDocument.id == source_id,
            SourceDocument.workspace_id == workspace_id,
        )
        .with_for_update()
    )
    if source is None:
        raise HTTPException(404, "Source not found")
    require_workspace_access(session, workspace_id, principal, "editor")
    version = session.scalar(
        select(DocumentVersion).where(
            DocumentVersion.id == version_id,
            DocumentVersion.source_document_id == source.id,
        )
    )
    if version is None:
        raise HTTPException(404, "Source version not found")
    _require_latest(session, source.id, version)
    existing = {
        p.chunk_id: p
        for p in session.scalars(
            select(KnowledgeProposal)
            .join(
                SourceChunk,
                SourceChunk.id == KnowledgeProposal.chunk_id,
            )
            .where(
                KnowledgeProposal.workspace_id == workspace_id,
                SourceChunk.document_version_id == version.id,
                KnowledgeProposal.extractor_version == EXTRACTOR_VERSION,
            )
        )
    }
    created = 0
    selected = []
    for chunk in session.scalars(
        select(SourceChunk)
        .where(
            SourceChunk.document_version_id == version.id,
        )
        .order_by(SourceChunk.ordinal)
    ):
        if not is_decision_chunk(chunk.text):
            continue
        proposal = existing.get(chunk.id)
        if proposal is None:
            proposal = KnowledgeProposal(
                workspace_id=workspace_id,
                chunk_id=chunk.id,
                statement=chunk.text,
                extractor_version=EXTRACTOR_VERSION,
                created_by=principal.user_id,
            )
            session.add(proposal)
            session.flush()
            created += 1
        selected.append(
            _proposal_read(
                *session.execute(
                    _proposal_query(workspace_id).where(KnowledgeProposal.id == proposal.id)
                ).one()
            )
        )
    return ExtractionRead(proposals=selected, created_count=created)


def list_proposals(
    session: Session,
    workspace_id: UUID,
    *,
    principal: Principal,
    status: ProposalFilter = "pending",
    limit: int = 50,
    offset: int = 0,
) -> list[ProposalRead]:
    require_workspace_access(session, workspace_id, principal, "editor")
    query = _proposal_query(workspace_id)
    if status != "all":
        query = query.where(KnowledgeProposal.status == status)
    rows = session.execute(
        query.order_by(KnowledgeProposal.created_at, KnowledgeProposal.id)
        .limit(limit)
        .offset(offset)
    )
    return [_proposal_read(*row) for row in rows]


def get_proposal(
    session: Session, workspace_id: UUID, proposal_id: UUID, *, principal: Principal
) -> ProposalRead:
    require_workspace_access(session, workspace_id, principal, "editor")
    row = session.execute(
        _proposal_query(workspace_id).where(KnowledgeProposal.id == proposal_id)
    ).one_or_none()
    if row is None:
        raise HTTPException(404, "Proposal not found")
    return _proposal_read(*row)


def review_proposal(
    session: Session,
    workspace_id: UUID,
    proposal_id: UUID,
    body: ReviewWrite,
    *,
    principal: Principal,
) -> ProposalRead:
    lock_owned_workspace(session, workspace_id, principal)
    query = _proposal_query(workspace_id).where(KnowledgeProposal.id == proposal_id)
    row = session.execute(query).one_or_none()
    if row is None:
        raise HTTPException(404, "Proposal not found")
    source = row[3]
    session.execute(
        select(SourceDocument.id)
        .where(
            SourceDocument.id == source.id,
            SourceDocument.workspace_id == workspace_id,
        )
        .with_for_update()
    )
    # Refresh after waiting: another review may have committed in the meantime.
    row = session.execute(
        query.with_for_update(of=KnowledgeProposal).execution_options(populate_existing=True)
    ).one()
    proposal, chunk, version, source, _, _ = row
    result_status = "approved" if body.action == "approve" else "rejected"
    if proposal.status != "pending":
        if proposal.status != result_status:
            raise HTTPException(409, "Proposal already has a different terminal review")
        return _proposal_read(*row)
    if body.action == "approve":
        _require_latest(session, source.id, version)
        # This is an exact extract, never an editable interpretation.
        if proposal.statement != chunk.text:
            raise HTTPException(409, "Proposal no longer matches its source evidence")
        session.add(ApprovedDecision(workspace_id=workspace_id, proposal_id=proposal.id))
    session.add(
        ReviewEvent(
            proposal_id=proposal.id,
            reviewer_id=principal.user_id,
            action=body.action,
            comment=body.comment,
        )
    )
    proposal.status = result_status
    session.flush()
    return _proposal_read(*session.execute(query).one())


def read_decisions(
    session: Session,
    workspace_id: UUID,
    *,
    principal: Principal,
    decision_id: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[DecisionRead]:
    require_workspace_access(session, workspace_id, principal)
    newer = aliased(DocumentVersion)
    query = (
        _proposal_query(workspace_id)
        .add_columns(
            ~exists().where(
                newer.source_document_id == SourceDocument.id,
                newer.version_number > DocumentVersion.version_number,
            ),
        )
        .where(
            ApprovedDecision.workspace_id == workspace_id,
            KnowledgeProposal.status == "approved",
            ReviewEvent.action == "approve",
        )
    )
    if decision_id is not None:
        query = query.where(ApprovedDecision.id == decision_id)
    rows = session.execute(
        query.order_by(ApprovedDecision.created_at, ApprovedDecision.id).limit(limit).offset(offset)
    )
    results = [
        DecisionRead(
            id=decision.id,
            workspace_id=workspace_id,
            proposal_id=proposal.id,
            statement=proposal.statement,
            evidence=_evidence(chunk, version, source),
            approved_by=event.reviewer_id,
            approved_at=event.created_at,
            source_is_latest=current,
        )
        for proposal, chunk, version, source, event, decision, current in rows
    ]
    if decision_id is not None and not results:
        raise HTTPException(404, "Decision not found")
    return results
