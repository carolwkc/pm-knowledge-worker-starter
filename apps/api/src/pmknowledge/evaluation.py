"""Evaluate synthetic retrieval cases with cached local weights; roll back fixture data."""

import argparse
import json
import platform
import sys
from hashlib import sha256
from importlib.metadata import version
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from pmknowledge.auth import Principal, create_user
from pmknowledge.config import Settings
from pmknowledge.documents import ingest
from pmknowledge.embeddings import Embedder, LocalEmbedder
from pmknowledge.evaluation_checks import (
    audit_answer,
    audit_evidence,
    audit_fixture,
    isolation_probes,
)
from pmknowledge.models import Workspace, WorkspaceMembership
from pmknowledge.retrieval import ask, search
from pmknowledge.schemas import Citation, QueryText, RetrievalMode, ShortText


class EvaluationDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: ShortText
    title: ShortText
    text: str = Field(min_length=1)


class EvaluationSpan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: ShortText
    start_char: int = Field(ge=0, strict=True)
    end_char: int = Field(gt=0, strict=True)


class EvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: ShortText
    query: QueryText
    relevant_document_ids: set[str]
    category: ShortText | None = None
    evidence_spans: list[EvaluationSpan] | None = None


class EvaluationDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
        documents = {document.id: document.text for document in self.documents}
        labelled = [case.evidence_spans is not None for case in self.cases]
        if any(labelled) and not all(labelled):
            raise ValueError("Supply evidence spans for every case or none (legacy dataset)")
        for case in self.cases:
            if case.evidence_spans is None:
                continue
            if {span.document_id for span in case.evidence_spans} != case.relevant_document_ids:
                raise ValueError("Support spans must agree with relevant document IDs")
            if len(set(case.evidence_spans)) != len(case.evidence_spans):
                raise ValueError("Support spans must be unique")
            for span in case.evidence_spans:
                content = documents[span.document_id]
                if (
                    not (span.start_char < span.end_char <= len(content))
                    or not content[span.start_char : span.end_char].strip()
                ):
                    raise ValueError("Support span must select nonblank text within its document")
        return self


def span_coverage(
    spans: list[EvaluationSpan], citations: list[Citation], labels: dict[str, str]
) -> tuple[int, int]:
    """Count relevant citations and distinct covered gold spans; callers audit citations first."""
    covered = {
        span
        for span in spans
        if any(
            labels.get(str(c.source_document_id)) == span.document_id
            and c.start_char <= span.start_char < span.end_char <= c.end_char
            for c in citations
        )
    }
    relevant = sum(
        any(
            labels.get(str(c.source_document_id)) == span.document_id
            and c.start_char <= span.start_char < span.end_char <= c.end_char
            for span in spans
        )
        for c in citations
    )
    return relevant, len(covered)


def ratio(numerator: float, denominator: int) -> dict[str, float | None]:
    return {
        "value": numerator / denominator if denominator else None,
        "numerator": numerator,
        "denominator": denominator,
    }


def answer_metrics(rows: list[dict[str, int | None]]) -> dict[str, Any]:
    labelled = [row for row in rows if row["expected"] is not None]
    positives = [row for row in labelled if row["expected"]]
    return {
        "citation_integrity": ratio(
            sum(row["valid"] or 0 for row in rows), sum(row["emitted"] or 0 for row in rows)
        ),
        "evidence_precision": ratio(
            sum(row["relevant"] or 0 for row in labelled),
            sum(row["emitted"] or 0 for row in labelled),
        ),
        "evidence_recall": ratio(
            sum((row["covered"] or 0) / (row["expected"] or 1) for row in positives),
            len(positives),
        ),
    }


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
    embedder: Embedder | None,
    k: int = 3,
    min_score: float = 0.6,
    *,
    selected_modes: tuple[RetrievalMode, ...] = ("keyword", "semantic", "hybrid"),
) -> dict[str, Any]:
    if (
        not 1 <= k <= 20
        or not selected_modes
        or any(mode not in ("keyword", "semantic", "hybrid") for mode in selected_modes)
        or len(set(selected_modes)) != len(selected_modes)
    ):
        raise ValueError("Require k=1..20 and distinct supported modes")
    savepoint = session.begin_nested()
    try:
        workspace = Workspace(name="Synthetic pilot evaluation")
        session.add(workspace)
        session.flush()
        user = create_user(session, "Synthetic evaluation user")
        session.add(WorkspaceMembership(workspace_id=workspace.id, user_id=user.id, role="owner"))
        session.flush()
        principal = Principal(user_id=user.id)
        labels = {}
        fixture_failures = []
        invalid_sources = set()
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
            errors = audit_fixture(
                session, workspace.id, receipt, document.text, document.title, principal
            )
            if errors:
                invalid_sources.add(str(receipt.source_document_id))
                fixture_failures.append({"document_id": document.id, "failures": errors})
        modes: dict[str, Any] = {}
        for mode in selected_modes:
            rankings, records, counts = [], [], []
            for case in dataset.cases:
                hits = search(
                    session,
                    workspace.id,
                    case.query,
                    k,
                    principal=principal,
                    mode=mode,
                    embedder=embedder,
                    min_score=min_score,
                )
                answer = ask(
                    session,
                    workspace.id,
                    case.query,
                    k,
                    principal=principal,
                    mode=mode,
                    embedder=embedder,
                    min_score=min_score,
                )
                failures, citation_errors = audit_answer(session, workspace.id, answer, principal)
                for hit in hits:
                    failures.extend(audit_evidence(session, workspace.id, hit, principal))
                    if str(hit.source_document_id) in invalid_sources:
                        failures.append("search_fixture_mismatch")
                    if str(hit.source_document_id) not in labels:
                        failures.append("unlabelled_search_source")
                if len({hit.chunk_id for hit in hits}) != len(hits) or len(hits) > k:
                    failures.append("duplicate_or_excess_search_hits")
                for index, errors in enumerate(citation_errors, 1):
                    source_id = str(answer.sources[index - 1].source_document_id)
                    if source_id in invalid_sources:
                        errors.append("fixture_mismatch")
                    if source_id not in labels:
                        errors.append("unlabelled_source")
                    failures.extend(f"citation_{index}:{error}" for error in errors)
                ranking = [labels.get(str(hit.source_document_id), "<unknown>") for hit in hits]
                rankings.append(ranking)
                valid = [
                    c
                    for c, errors in zip(answer.sources, citation_errors, strict=True)
                    if not errors
                ]
                relevant, covered = (
                    (None, None)
                    if case.evidence_spans is None
                    else span_coverage(case.evidence_spans, valid, labels)
                )
                count = {
                    "emitted": len(answer.sources),
                    "valid": len(valid),
                    "relevant": relevant,
                    "covered": covered,
                    "expected": len(case.evidence_spans)
                    if case.evidence_spans is not None
                    else None,
                }
                counts.append(count)
                records.append(
                    {
                        "id": case.id,
                        "category": case.category,
                        "query": case.query,
                        "retrieved": ranking,
                        "relevant": sorted(case.relevant_document_ids),
                        "search_hits": [hit.model_dump(mode="json") for hit in hits],
                        "answer": answer.model_dump(mode="json"),
                        "evidence_counts": count,
                        "failures": failures,
                    }
                )
            probes = isolation_probes(session, mode, embedder, min_score)
            modes[mode] = {
                **retrieval_metrics(rankings, [c.relevant_document_ids for c in dataset.cases], k),
                "answer_metrics": answer_metrics(counts),
                "cases": records,
                "probes": probes,
                "passed": not fixture_failures
                and not any(record["failures"] for record in records)
                and probes["passed"],
            }
        return {
            "report_version": 2,
            "fixture_failures": fixture_failures,
            "passed": all(result["passed"] for result in modes.values()),
            "model_id": embedder.model_id if embedder is not None else None,
            "k": k,
            "semantic_min_score": min_score,
            "documents": len(dataset.documents),
            "queries": len(dataset.cases),
            "positive_queries": sum(bool(case.relevant_document_ids) for case in dataset.cases),
            "negative_queries": sum(not case.relevant_document_ids for case in dataset.cases),
            "modes": modes,
            "settings": {
                "answer_max_citations": 3,
                "hybrid_candidates_per_retriever": 20,
                "rrf_k": 60,
                "selected_modes": list(selected_modes),
            },
        }
    finally:
        savepoint.rollback()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=Path("apps/api/evaluation/cases.json"))
    parser.add_argument("--k", type=int, choices=range(1, 21), default=3)
    parser.add_argument(
        "--modes",
        nargs="+",
        choices=("keyword", "semantic", "hybrid"),
        default=["keyword", "semantic", "hybrid"],
    )
    args = parser.parse_args()
    engine: Engine | None = None
    try:
        settings = Settings()
        engine = create_engine(settings.database_url, hide_parameters=True)
        raw_cases = args.cases.read_bytes()
        dataset = EvaluationDataset.model_validate_json(raw_cases)
        embedder = (
            LocalEmbedder(settings.embedding_cache_dir)
            if any(mode != "keyword" for mode in args.modes)
            else None
        )
        with Session(engine) as session:
            result = evaluate(
                session,
                dataset,
                embedder,
                args.k,
                settings.semantic_min_score,
                selected_modes=tuple(args.modes),
            )
        result["cases_sha256"] = sha256(raw_cases).hexdigest()
        result["fastembed_version"] = version("fastembed")
        result["runtime"] = {
            "python": platform.python_version(),
            "sqlalchemy": version("sqlalchemy"),
            "onnxruntime": version("onnxruntime"),
        }
        print(json.dumps(result, indent=2))
        if not result["passed"]:
            raise SystemExit(1)
    except Exception as exc:
        # Never echo database URLs, submitted contents, or third-party exception payloads.
        print(
            f"Evaluation incomplete ({type(exc).__name__}); check dataset, database and "
            "cached local weights. No mode was substituted.",
            file=sys.stderr,
        )
        raise SystemExit(2) from None
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()
