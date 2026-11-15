from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

ShortText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200, pattern=r"^[^\x00]+$"),
]
QueryText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=1000, pattern=r"^[^\x00]+$"),
]
RetrievalMode = Literal["keyword", "semantic", "hybrid"]
WorkspaceRole = Literal["reader", "editor", "owner"]


class UserCreate(BaseModel):
    name: ShortText


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    created_at: datetime


class WorkspaceCreate(BaseModel):
    name: ShortText


class WorkspaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    created_at: datetime


class JoinedWorkspace(WorkspaceRead):
    role: WorkspaceRole


class WorkspaceList(BaseModel):
    workspaces: list[JoinedWorkspace]


class MembershipWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: WorkspaceRole


class MembershipRead(MembershipWrite):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID


class MembershipList(BaseModel):
    members: list[MembershipRead]


class IngestRead(BaseModel):
    workspace_id: UUID
    source_document_id: UUID
    document_version_id: UUID
    version_number: int
    sha256: str
    chunk_count: int
    duplicate: bool


class SourceVersionRead(BaseModel):
    workspace_id: UUID
    source_document_id: UUID
    document_version_id: UUID
    title: str
    external_uri: str | None
    version_number: int
    sha256: str
    ingested_at: datetime
    plain_text: str
    source_is_latest: bool


class Evidence(BaseModel):
    source_document_id: UUID
    document_version_id: UUID
    chunk_id: UUID
    title: str
    external_uri: str | None
    ordinal: int
    excerpt: str
    start_char: int
    end_char: int


class SearchHit(Evidence):
    score: float


class SearchRead(BaseModel):
    results: list[SearchHit]


class AskRequest(BaseModel):
    question: QueryText
    limit: Annotated[int, Field(ge=1, le=20)] = 5
    mode: RetrievalMode = "keyword"


class Citation(Evidence):
    citation: str


class AnswerRead(BaseModel):
    answer: str
    status: Literal["grounded", "insufficient_evidence"]
    sources: list[Citation]


ProposalStatus = Literal["pending", "approved", "rejected"]
ProposalFilter = Literal["pending", "approved", "rejected", "all"]
ReviewAction = Literal["approve", "reject"]


class ReviewWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: ReviewAction
    comment: QueryText | None = None


class ReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reviewer_id: UUID
    action: ReviewAction
    comment: str | None
    created_at: datetime


class ProposalRead(BaseModel):
    id: UUID
    workspace_id: UUID
    kind: Literal["decision"] = "decision"
    statement: str
    evidence: Evidence
    extraction_method: Literal["deterministic_source_quotation"] = "deterministic_source_quotation"
    extractor_version: str
    created_by: UUID
    created_at: datetime
    status: ProposalStatus
    review: ReviewRead | None
    decision_id: UUID | None


class ProposalList(BaseModel):
    proposals: list[ProposalRead]


class ExtractionRead(ProposalList):
    created_count: int


class DecisionRead(BaseModel):
    id: UUID
    workspace_id: UUID
    proposal_id: UUID
    statement: str
    evidence: Evidence
    approved_by: UUID
    approved_at: datetime
    source_is_latest: bool


class DecisionList(BaseModel):
    decisions: list[DecisionRead]
