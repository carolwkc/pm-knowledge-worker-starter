"""Offline AI-review diagnostics; no inference, policy tuning or human findings."""

import argparse
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from pmknowledge.evaluation import EvaluationSpan
from pmknowledge.support_review import (
    RUBRIC,
    Judgments,
    bundle_parts,
    checked_capture,
    digest,
    encoded,
    literal_block,
    load_json,
    statistics,
    validate_judgment,
)


class ReviewerProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    agent_id: str = Field(min_length=1)
    model: str | None  # Null explicitly means the harness did not expose the model.
    review_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    method: str = Field(min_length=1)
    rubric_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class AIReview(Judgments):
    review_kind: Literal["ai"]
    provenance: ReviewerProvenance


def trace_span(
    span: EvaluationSpan,
    documents: dict[str, str],
    record: dict[str, Any],
    labels: dict[str, str],
) -> dict[str, Any]:
    def contains(excerpt: dict[str, Any]) -> bool:
        return (
            labels[excerpt["source_document_id"]] == span.document_id
            and excerpt["start_char"] <= span.start_char < span.end_char <= excerpt["end_char"]
        )

    return {
        **span.model_dump(),
        "text": documents[span.document_id][span.start_char : span.end_char],
        "candidate_ranks": [
            rank for rank, hit in enumerate(record["search_hits"], 1) if contains(hit)
        ],
        "emitted_citations": [
            citation["citation"] for citation in record["answer"]["sources"] if contains(citation)
        ],
    }


def build_diagnostics(bundle: Path, ai_review: Path) -> dict[str, Any]:
    files, manifest = bundle_parts(
        (bundle / "cases.json").read_bytes(), (bundle / "capture.json").read_bytes()
    )
    for name in ("manifest.json", "packet.md"):
        if (bundle / name).read_bytes() != files[name]:
            raise ValueError("Immutable bundle changed")
    raw_review = ai_review.read_bytes()
    form = AIReview.model_validate(load_json(raw_review))
    date.fromisoformat(form.provenance.review_date)
    if form.manifest_sha256 != digest(files["manifest.json"]):
        raise ValueError("AI review belongs to another bundle")
    if form.provenance.rubric_sha256 != digest(RUBRIC.encode()):
        raise ValueError("AI review rubric differs from the bundled rubric")
    if not all(
        value.strip()
        for value in (form.reviewer_id, form.provenance.agent_id, form.provenance.method)
    ) or (form.provenance.model is not None and not form.provenance.model.strip()):
        raise ValueError("Reviewer provenance must be explicit; use null for unknown model")
    expected = {item["item_id"] for item in manifest["items"]}
    if len(form.items) != len(expected) or {row.item_id for row in form.items} != expected:
        raise ValueError("Require every item exactly once")
    if any(row.verdict is None for row in form.items):
        raise ValueError("Require a complete AI review; uncertainty is an explicit verdict")
    dataset, capture = checked_capture(files["cases.json"], files["capture.json"])
    records = {
        (record["id"], mode): record
        for mode, result in capture["modes"].items()
        for record in result["cases"]
    }
    cases = {case.id: case for case in dataset.cases}
    documents = {doc.id: doc.text for doc in dataset.documents}
    judgments = {row.item_id: row for row in form.items}
    rows = []
    for identity in manifest["items"]:
        judgment = judgments[identity["item_id"]]
        record = records[identity["case_id"], identity["mode"]]
        validate_judgment(judgment, record, dataset, capture["document_labels"])
        authored = [
            trace_span(span, documents, record, capture["document_labels"])
            for span in cases[identity["case_id"]].evidence_spans or []
        ]
        ai_evidence = [
            trace_span(span, documents, record, capture["document_labels"])
            for span in judgment.evidence_spans
        ]
        findings = []
        # These tags describe containment, not whether a semantic judgment is correct.
        for prefix, traces in (("", authored), ("ai_evidence_", ai_evidence)):
            if any(not trace["candidate_ranks"] for trace in traces):
                findings.append(f"{prefix}candidate_gap")
            if any(trace["candidate_ranks"] and not trace["emitted_citations"] for trace in traces):
                findings.append(f"{prefix}selection_gap")
        if record["answer"]["status"] == "grounded":
            if identity["category"] == "missing_fact" and judgment.verdict == "unsupported":
                findings.append("missing_fact_grounded")
            if judgment.verdict == "conflicting":
                findings.append("unresolved_conflict_grounded")
        rows.append(
            {
                **identity,
                "question": record["query"],
                "response_status": record["answer"]["status"],
                "ai_judgment": judgment.model_dump(exclude={"item_id"}),
                "authored_support": authored,
                "ai_evidence": ai_evidence,
                "findings": findings,
            }
        )
    ordered_judgments = [judgments[row["item_id"]] for row in rows]
    return {
        "schema_version": 1,
        "review_kind": "ai",
        "status": "ai_review_complete",
        "interpretation": (
            "AI judgments on an authored synthetic packet, not human findings, factual truth, "
            "representative performance or a release gate. Span containment is mechanical; "
            "it does not validate semantic support. Task 012 is observed diagnostic data."
        ),
        "reviewer_id": form.reviewer_id,
        "provenance": form.provenance.model_dump(),
        "manifest_sha256": form.manifest_sha256,
        "ai_review_sha256": digest(raw_review),
        "source_hashes": manifest["files"],
        "candidate_budget": capture["k"],
        "overall": statistics(ordered_judgments),
        **{
            f"by_{key}": {
                value: statistics([judgments[row["item_id"]] for row in rows if row[key] == value])
                for value in sorted({row[key] for row in rows})
            }
            for key in ("mode", "category")
        },
        "response_status_counts": dict(Counter(row["response_status"] for row in rows)),
        "finding_counts": dict(Counter(tag for row in rows for tag in row["findings"])),
        "items": rows,
    }


def render_report(report: dict[str, Any]) -> bytes:
    parts = [
        "# Task 013 — AI review and offline support diagnosis\n",
        report["interpretation"] + "\n",
        "Human judgments are separate and are not read or modified by this command. "
        "No human completion is implied and no production policy is changed. "
        "Unknown model metadata is recorded as null.\n",
        "## Bound inputs and AI reviewer\n",
        literal_block(
            encoded(
                {
                    key: report[key]
                    for key in (
                        "reviewer_id",
                        "provenance",
                        "manifest_sha256",
                        "ai_review_sha256",
                        "source_hashes",
                    )
                }
            )
            .decode()
            .rstrip()
        ),
        "## AI judgment counts\n",
        "| Mode | Full | Partial | Unsupported | Conflicting | Reviewed |\n"
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for mode, summary in {**report["by_mode"], "overall": report["overall"]}.items():
        counts = summary["verdict_counts"]
        parts.append(
            f"| {mode} | {counts['fully_supported']} | {counts['partially_supported']} | "
            f"{counts['unsupported']} | {counts['conflicting']} | {summary['reviewed']} |"
        )
    parts.extend(
        [
            "\nAll verdict counts, uncertainty and denominators are recorded in diagnostics.json. "
            "AI full-support rate excludes abstentions and uncertainty; "
            "completion is not quality.\n",
            literal_block(
                encoded(
                    {
                        "response_status_counts": report["response_status_counts"],
                        "finding_counts": report["finding_counts"],
                    }
                )
                .decode()
                .rstrip()
            ),
            "## Reading the traces\n",
            "Authored support comes from dataset labels. "
            "AI evidence comes from reviewer citations, "
            "which can include opposing positions or context rather than support. Candidate ranks "
            "are one-based; citation numbers refer to the emitted answer. Each original half-open "
            "Unicode codepoint span must be fully contained in a candidate/quotation to count. "
            "CRLF counts as two characters and emoji as one. Empty reference lists prove nothing "
            "about answerability.\n",
            "`candidate_gap` and `selection_gap` use authored support spans. Their `ai_evidence_` "
            "counterparts use AI-cited spans. A selection gap means a span was retrieved but not "
            "emitted; a candidate gap means it is absent "
            "from this bounded capture, not the corpus. "
            "Grounded-response tags combine the AI verdict with the captured status/category. "
            "Findings overlap and must not be summed as disjoint failures.\n",
            "## Prioritized engineering handoff\n",
        ]
    )
    recommendations = [
        (
            "1. Investigate safe abstention and unresolved-conflict handling",
            {"missing_fact_grounded", "unresolved_conflict_grounded"},
            "Observed: the linked grounded responses are tagged as AI-reviewed missing facts "
            "or unresolved conflicts. Hypothesis: requested-fact and scope checks could improve "
            "abstention. Similar words, numbers or currency do not establish the requested fact. "
            "Do not resolve policy authority from ranking or treat both-position questions as "
            "requests for one authoritative position.",
        ),
        (
            "2. Investigate bounded candidate recall",
            {"candidate_gap"},
            "Observed: at least one authored support span is absent from the bounded candidate "
            "set in each linked item. Reranking those candidates cannot recover absent spans. "
            "Hypothesis: candidate assembly or ranking changes may recover them; not tested here.",
        ),
        (
            "3. Investigate quotation coverage",
            {"selection_gap", "ai_evidence_selection_gap"},
            "Observed: authored support or AI-cited spans reached candidates but were not emitted "
            "in the linked items. Candidate ranks and citation lists below expose the exact gap. "
            "The frozen selector keeps the first three qualifying unique excerpts using overlap "
            "OR cosine; it has no requested-fact or contradiction check. Hypothesis: a coverage "
            "objective could help; raising thresholds alone is not established as a fix. "
            "Source: `apps/api/src/pmknowledge/answer_selection.py`.",
        ),
    ]
    for title, tags, description in recommendations:
        affected = [row for row in report["items"] if tags.intersection(row["findings"])]
        if affected:
            parts.extend(
                [
                    f"### {title}\n",
                    description + "\n",
                    "Evidence: "
                    + ", ".join(
                        f"[{row['mode']} / {row['item_id'][:12]}](#item-{row['item_id']})"
                        for row in affected
                    )
                    + "\n",
                ]
            )
    controls = [
        row for row in report["items"] if row["ai_judgment"]["verdict"] == "fully_supported"
    ]
    parts.append(
        "Successful controls: "
        + ", ".join(
            f"[{row['mode']} / {row['item_id'][:12]}](#item-{row['item_id']})" for row in controls
        )
        + ".\n"
        if controls
        else "No fully supported AI judgments in this review.\n"
    )
    parts.extend(
        [
            "Extra irrelevant quotations can coexist with "
            "full requested-fact support. A request to report both memo positions differs from "
            "a request to resolve which position is authoritative.\n",
            "Before any production change, test a concrete alternative against fresh frozen "
            "validation plus permission/provenance checks. This report runs no experiment or "
            "replacement algorithm and claims no effectiveness. One AI reviewer, visible authored "
            "corpus and no human agreement measurement limit these findings.\n",
        ]
    )
    for row in report["items"]:
        parts.extend(
            [
                f"## Item {row['item_id']}\n",
                literal_block(encoded(row).decode().rstrip()),
            ]
        )
    return ("\n".join(parts).rstrip() + "\n").encode()


def export_diagnostics(bundle: Path, ai_review: Path, output_dir: Path) -> dict[str, Any]:
    if output_dir.resolve().is_relative_to(bundle.resolve()):
        raise ValueError("Output must be outside the immutable input bundle")
    report = build_diagnostics(bundle, ai_review)
    outputs = {"diagnostics.json": encoded(report), "report.md": render_report(report)}
    output_dir.mkdir(parents=True, exist_ok=False)
    for name, raw in outputs.items():
        (output_dir / name).write_bytes(raw)
    return {
        "schema_version": 1,
        "status": report["status"],
        "review_kind": "ai",
        "items": len(report["items"]),
        "files": {name: digest(raw) for name, raw in outputs.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--ai-review", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(
            encoded(export_diagnostics(args.bundle, args.ai_review, args.output_dir)).decode(),
            end="",
        )
    except Exception as exc:
        print(
            f"Support diagnostics incomplete ({type(exc).__name__}); check inputs and output.",
            file=sys.stderr,
        )
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
