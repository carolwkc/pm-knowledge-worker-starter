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


class WorkspaceCreate(BaseModel):
    name: ShortText


class WorkspaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    created_at: datetime


class IngestRead(BaseModel):
    workspace_id: UUID
    source_document_id: UUID
    document_version_id: UUID
    version_number: int
    sha256: str
    chunk_count: int
    duplicate: bool


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


class Citation(Evidence):
    citation: str


class AnswerRead(BaseModel):
    answer: str
    status: Literal["grounded", "insufficient_evidence"]
    sources: list[Citation]
