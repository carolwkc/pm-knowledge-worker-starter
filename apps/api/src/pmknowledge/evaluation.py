"""Evaluate synthetic retrieval cases with cached local weights; roll back fixture data."""

import argparse
import json
from hashlib import sha256
from importlib.metadata import version
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from pmknowledge.auth import Principal, create_user
from pmknowledge.config import Settings
from pmknowledge.documents import ingest
from pmknowledge.embeddings import Embedder, LocalEmbedder
from pmknowledge.models import Workspace, WorkspaceMembership
from pmknowledge.retrieval import search
from pmknowledge.schemas import QueryText, RetrievalMode, ShortText


class EvaluationDocument(BaseModel):
    id: ShortText
    title: ShortText
    text: str = Field(min_length=1)


class EvaluationCase(BaseModel):
    id: ShortText
    query: QueryText
    relevant_document_ids: set[str]


class EvaluationDataset(BaseModel):
    documents: list[EvaluationDocument] = Field(min_length=1)
    cases: list[EvaluationCase] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_ids(self) -> "EvaluationDataset":
        ids = {document.id for document in self.documents}
        if len(ids) != len(self.documents) or len({case.id for case in self.cases}) != len(
            self.cases
        ):
            raise ValueError("Evaluation IDs must be unique")
        if any(not case.relevant_document_ids <= ids for case in self.cases):
            raise ValueError("Relevance labels must reference known evaluation document IDs")
        return self


def retrieval_metrics(
    rankings: list[list[str]], relevant: list[set[str]], k: int
) -> dict[str, float | None]:
    if k < 1 or len(rankings) != len(relevant):
        raise ValueError("Metrics require positive k and aligned rankings/labels")
    recalls, reciprocals, abstentions = [], [], []
    for ranking, expected in zip(rankings, relevant, strict=True):
        top = ranking[:k]
        if not expected:
            abstentions.append(float(not top))
            continue
        recalls.append(len(set(top) & expected) / len(expected))
        reciprocals.append(
            next((1 / rank for rank, doc in enumerate(top, 1) if doc in expected), 0.0)
        )
    return {
        "recall_at_k": sum(recalls) / len(recalls) if recalls else None,
        "mrr_at_k": sum(reciprocals) / len(reciprocals) if reciprocals else None,
        "no_evidence_accuracy": sum(abstentions) / len(abstentions) if abstentions else None,
    }


def evaluate(
    session: Session,
    dataset: EvaluationDataset,
    embedder: Embedder,
    k: int = 3,
    min_score: float = 0.6,
) -> dict[str, Any]:
    savepoint = session.begin_nested()
    try:
        workspace = Workspace(name="Task 002 synthetic evaluation")
        session.add(workspace)
        session.flush()
        user = create_user(session, "Synthetic evaluation user")
        session.add(WorkspaceMembership(workspace_id=workspace.id, user_id=user.id, role="owner"))
        session.flush()
        principal = Principal(user_id=user.id)
        labels = {}
        for document in dataset.documents:
            receipt = ingest(
                session,
                workspace.id,
                UploadFile(
                    file=BytesIO(document.text.encode("utf-8")), filename=f"{document.id}.txt"
                ),
                principal=principal,
                title=document.title,
                embedder=embedder,
            )
            labels[str(receipt.source_document_id)] = document.id
        modes: dict[str, Any] = {}
        selected_modes: tuple[RetrievalMode, ...] = ("keyword", "semantic", "hybrid")
        for mode in selected_modes:
            rankings = [
                [
                    labels[str(hit.source_document_id)]
                    for hit in search(
                        session,
                        workspace.id,
                        case.query,
                        k,
                        principal=principal,
                        mode=mode,
                        embedder=embedder,
                        min_score=min_score,
                    )
                ]
                for case in dataset.cases
            ]
            modes[mode] = {
                **retrieval_metrics(rankings, [c.relevant_document_ids for c in dataset.cases], k),
                "cases": [
                    {
                        "id": case.id,
                        "retrieved": ranking,
                        "relevant": sorted(case.relevant_document_ids),
                    }
                    for case, ranking in zip(dataset.cases, rankings, strict=True)
                ],
            }
        return {
            "model_id": embedder.model_id,
            "k": k,
            "semantic_min_score": min_score,
            "documents": len(dataset.documents),
            "queries": len(dataset.cases),
            "positive_queries": sum(bool(case.relevant_document_ids) for case in dataset.cases),
            "negative_queries": sum(not case.relevant_document_ids for case in dataset.cases),
            "modes": modes,
        }
    finally:
        savepoint.rollback()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=Path("apps/api/evaluation/cases.json"))
    parser.add_argument("--k", type=int, choices=range(1, 21), default=3)
    args = parser.parse_args()
    settings = Settings()
    raw_cases = args.cases.read_bytes()
    dataset = EvaluationDataset.model_validate_json(raw_cases)
    engine = create_engine(settings.database_url, hide_parameters=True)
    try:
        with Session(engine) as session:
            result = evaluate(
                session,
                dataset,
                LocalEmbedder(settings.embedding_cache_dir),
                args.k,
                settings.semantic_min_score,
            )
        result["cases_sha256"] = sha256(raw_cases).hexdigest()
        result["fastembed_version"] = version("fastembed")
        print(json.dumps(result, indent=2))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
