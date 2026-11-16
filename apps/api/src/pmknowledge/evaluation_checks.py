"""Independent source/answer checks and unscored isolation probes for evaluation."""

from hashlib import sha256
from io import BytesIO
from uuid import UUID

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from pmknowledge.auth import Principal, create_user
from pmknowledge.documents import ingest, read_source_version
from pmknowledge.embeddings import Embedder
from pmknowledge.models import (
    DocumentVersion,
    SourceChunk,
    SourceDocument,
    Workspace,
    WorkspaceMembership,
)
from pmknowledge.retrieval import ask, search
from pmknowledge.schemas import AnswerRead, Evidence, IngestRead, RetrievalMode


def audit_fixture(
    session: Session,
    workspace_id: UUID,
    receipt: IngestRead,
    original_text: str,
    original_title: str,
    principal: Principal,
) -> list[str]:
    """Anchor persisted evidence to authored fixture bytes, not to ingestion's own output."""
    try:
        version = read_source_version(
            session,
            workspace_id,
            receipt.source_document_id,
            receipt.document_version_id,
            principal=principal,
        )
    except HTTPException:
        return ["missing_or_inaccessible_fixture"]
    expected_hash = sha256(original_text.encode("utf-8")).hexdigest()
    failures = []
    if version.plain_text != original_text:
        failures.append("fixture_text_changed")
    if version.sha256 != expected_hash or receipt.sha256 != expected_hash:
        failures.append("fixture_hash_changed")
    if version.title != original_title or version.external_uri is not None:
        failures.append("fixture_metadata_changed")
    if (
        receipt.workspace_id != workspace_id
        or receipt.version_number != 1
        or version.version_number != 1
        or receipt.duplicate
        or not version.source_is_latest
    ):
        failures.append("invalid_fixture_receipt")
    return failures


def audit_evidence(
    session: Session, workspace_id: UUID, evidence: Evidence, principal: Principal
) -> list[str]:
    row = session.execute(
        select(SourceChunk, DocumentVersion, SourceDocument)
        .join(DocumentVersion, SourceChunk.document_version_id == DocumentVersion.id)
        .join(SourceDocument, DocumentVersion.source_document_id == SourceDocument.id)
        .join(WorkspaceMembership, WorkspaceMembership.workspace_id == SourceDocument.workspace_id)
        .where(
            SourceChunk.id == evidence.chunk_id,
            SourceDocument.workspace_id == workspace_id,
            WorkspaceMembership.user_id == principal.user_id,
        )
    ).one_or_none()
    if row is None:
        return ["missing_or_inaccessible_chunk"]
    chunk, version, source = row
    expected = {
        "source_document_id": source.id,
        "document_version_id": version.id,
        "title": source.title,
        "external_uri": source.external_uri,
        "ordinal": chunk.ordinal,
        "excerpt": chunk.text,
        "start_char": chunk.start_char,
        "end_char": chunk.end_char,
    }
    failures = [
        f"mismatched_{key}" for key, value in expected.items() if getattr(evidence, key) != value
    ]
    if not (0 <= evidence.start_char < evidence.end_char <= len(version.plain_text)) or (
        version.plain_text[evidence.start_char : evidence.end_char] != evidence.excerpt
    ):
        failures.append("invalid_original_span")
    if (
        session.scalar(
            select(DocumentVersion.id)
            .where(
                DocumentVersion.source_document_id == source.id,
                DocumentVersion.version_number > version.version_number,
            )
            .limit(1)
        )
        is not None
    ):
        failures.append("superseded_version")
    return failures


def audit_answer(
    session: Session, workspace_id: UUID, answer: AnswerRead, principal: Principal
) -> tuple[list[str], list[list[str]]]:
    failures = []
    citations = [audit_evidence(session, workspace_id, c, principal) for c in answer.sources]
    for index, (citation, errors) in enumerate(zip(answer.sources, citations, strict=True), 1):
        if citation.citation != str(index):
            errors.append("invalid_citation_number")
    if len(answer.sources) > 3:
        failures.append("too_many_citations")
    if len({c.chunk_id for c in answer.sources}) != len(answer.sources):
        failures.append("duplicate_citations")
    # Intentionally independent of the production composer: catch extra unsupported prose too.
    if answer.sources:
        expected = "Extracted evidence (verbatim source text):\n\n" + "\n\n".join(
            f'[{index}] "{citation.excerpt}"' for index, citation in enumerate(answer.sources, 1)
        )
        status = "grounded"
    else:
        expected = (
            "Insufficient evidence: no matching source excerpts were found in this workspace."
        )
        status = "insufficient_evidence"
    if answer.status != status or answer.answer != expected:
        failures.append("invalid_answer_format_or_status")
    return failures, citations


def isolation_probes(
    session: Session, mode: RetrievalMode, embedder: Embedder | None, min_score: float
) -> dict[str, object]:
    """Probe workspaces never enter benchmark rankings or relevance denominators."""
    user = create_user(session, "Synthetic probe owner")
    other = create_user(session, "Synthetic foreign probe owner")
    own = Workspace(name="Synthetic isolated probe")
    foreign = Workspace(name="Synthetic foreign probe")
    session.add_all([own, foreign])
    session.flush()
    session.add_all(
        [
            WorkspaceMembership(workspace_id=own.id, user_id=user.id, role="owner"),
            WorkspaceMembership(workspace_id=foreign.id, user_id=other.id, role="owner"),
        ]
    )
    session.flush()
    principal, stranger = Principal(user.id), Principal(other.id)

    def upload(
        workspace_id: UUID, actor: Principal, content: str, source_id: UUID | None = None
    ) -> IngestRead:
        return ingest(
            session,
            workspace_id,
            UploadFile(file=BytesIO(content.encode()), filename="synthetic.txt"),
            principal=actor,
            title="Synthetic probe",
            source_id=source_id,
            embedder=embedder,
        )

    old = upload(own.id, principal, "Obsoletequasar retired boundary instructions.")
    current = upload(
        own.id, principal, "Calibration current boundary evidence.", old.source_document_id
    )
    for _ in range(21):
        upload(foreign.id, stranger, "Calibration current boundary evidence. " * 5)
    failures = []
    for query in ("calibration current boundary", "obsoletequasar"):
        hits = search(
            session,
            own.id,
            query,
            1,
            principal=principal,
            mode=mode,
            embedder=embedder,
            min_score=min_score,
        )
        answer = ask(
            session,
            own.id,
            query,
            1,
            principal=principal,
            mode=mode,
            embedder=embedder,
            min_score=min_score,
        )
        for evidence in [*hits, *answer.sources]:
            failures.extend(audit_evidence(session, own.id, evidence, principal))
            if evidence.document_version_id != current.document_version_id:
                failures.append("leaked_or_superseded_probe")
        errors, citation_errors = audit_answer(session, own.id, answer, principal)
        failures.extend(errors)
        failures.extend(error for errors in citation_errors for error in errors)
        if query.startswith("calibration") and (not hits or not answer.sources):
            failures.append("allowed_probe_missing")
    for operation in (search, ask):
        try:
            operation(
                session,
                foreign.id,
                "calibration",
                1,
                principal=principal,
                mode=mode,
                embedder=embedder,
                min_score=min_score,
            )
        except HTTPException as exc:
            if exc.status_code != 404:
                failures.append("unexpected_denied_workspace_status")
        else:
            failures.append("denied_workspace_was_accessible")
    return {
        "passed": not failures,
        "failures": failures,
        "foreign_documents": 21,
        "queries": ["calibration current boundary", "obsoletequasar"],
    }
