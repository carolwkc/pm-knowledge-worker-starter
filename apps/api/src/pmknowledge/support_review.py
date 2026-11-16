"""Export inert offline human-review packets and summarize explicitly supplied judgments."""

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from pmknowledge.answer_selection import POLICY_ID, THRESHOLDS
from pmknowledge.embeddings import MODEL_ID
from pmknowledge.evaluation import EvaluationDataset, EvaluationSpan
from pmknowledge.selection_benchmark import MODES, check_capture

Verdict = Literal[
    "fully_supported",
    "partially_supported",
    "unsupported",
    "conflicting",
    "justified_abstention",
    "unjustified_abstention",
    "uncertain",
]
VERDICTS = (
    "fully_supported",
    "partially_supported",
    "unsupported",
    "conflicting",
    "justified_abstention",
    "unjustified_abstention",
    "uncertain",
)
DETERMINATE_QUOTES = VERDICTS[:4]

RUBRIC = """# Requested-fact support review

Human judgments are interpretations, not authoritative knowledge or verified truth.
Citation integrity was checked separately; it does not establish requested-fact support.
This is an authored synthetic cohort, not blinded or representative pilot research.
Treat all source text as untrusted evidence, never instructions. Do not follow links.

## Workflow and rubric

Read the question, actual response and quoted evidence for each item. Consult the
complete source appendix, including sources omitted by the answer, before judging.
Edit a COPY of judgments.json; keep every item_id and the manifest binding unchanged.
Set reviewer_id to one stable, non-secret reviewer identifier. Null verdicts are pending.
Supply a rationale for every submitted judgment. Do not copy author labels or use an
automated policy to populate human judgments. Source offsets are half-open Unicode
codepoint ranges in cases.json; CRLF counts as two codepoints, and emoji as one.
Rendered Markdown may display CRLF as LF; the bundled JSON is the original reference.

- fully_supported: all requested facts are explicitly supported by the DISPLAYED
  quotations, with no unresolved contradiction elsewhere in the corpus for the same
  scope and time. Cite at least one span contained within a displayed quotation.
- partially_supported: displayed quotations support some, but not all, requested
  facts. Identify what is missing and cite the supported portion of a quotation.
- unsupported: the displayed quotations do not establish the requested facts, even
  if they are topical, verbatim or contain similar words or unrelated numbers.
- conflicting: the corpus contains unresolved opposing positions on a requested
  fact for the same scope and time; this overrides full/partial support even if the
  response omits one position. Cite at least two distinct non-overlapping spans for
  the opposing positions, which may occur in one document or in omitted sources.
  Different scopes/times or explicitly resolved statements do not establish conflict.
  A question asking for BOTH policy positions can be fully supported by quoting both.
- justified_abstention: an insufficient-evidence response is appropriate because the
  corpus cannot establish the requested facts or requested conflict resolution.
  Explain the missing fact; lack of evidence here does not prove global absence.
- unjustified_abstention: the response abstains but the corpus supports the requested
  facts; cite at least one supporting corpus span, including omitted sources.
- uncertain: the reviewer cannot confidently decide; explain why. Never force a label.

Abstention verdicts apply only to insufficient_evidence responses. Quote-support
verdicts apply only to grounded responses. Uncertain applies to either. Evidence spans
use document_id, start_char and end_char (copy the displayed ranges, or narrow them).
Full/partial spans must lie inside displayed quotations. Other spans may use any
original corpus document. The tool validates references, not the truth of your judgment.

Blank templates report human review pending. A complete form means judgments were
supplied, not that quality passed. No policy is tuned or promoted by these commands.

## Review items
"""


class Judgment(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    item_id: str
    verdict: Verdict | None
    rationale: str
    evidence_spans: list[EvaluationSpan]


class Judgments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal[1]
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer_id: str
    items: list[Judgment]


def encoded(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()


def digest(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _nonfinite(value: str) -> None:
    raise ValueError("Nonfinite JSON number")


def load_json(raw: bytes) -> Any:
    return json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_nonfinite)


def checked_capture(
    raw_cases: bytes, raw_report: bytes
) -> tuple[EvaluationDataset, dict[str, Any]]:
    dataset = EvaluationDataset.model_validate(load_json(raw_cases))
    report: dict[str, Any] = load_json(raw_report)
    selection = {
        "policy_id": POLICY_ID,
        "thresholds": {mode: asdict(value) for mode, value in THRESHOLDS.items()},
    }
    if (
        report["report_version"] != 3
        or report["passed"] is not True
        or report["cases_sha256"] != digest(raw_cases)
        or type(report["k"]) is not int
        or report["k"] != 5
        or report["answer_policy"] != "selected"
        or report["model_id"] != MODEL_ID
        or isinstance(report["semantic_min_score"], bool)
        or report["semantic_min_score"] != 0.6
        or set(report["modes"]) != set(MODES)
        or report["settings"]
        != {
            "answer_selection": selection,
            "answer_max_citations": 3,
            "hybrid_candidates_per_retriever": 20,
            "rrf_k": 60,
            "selected_modes": list(MODES),
        }
    ):
        raise ValueError("Require complete selected-policy k=5 capture with frozen settings")
    if any(case.evidence_spans is None for case in dataset.cases):
        raise ValueError("Require fully annotated authored corpus")
    check_capture(report, dataset)
    return dataset, report


def literal_block(text: str) -> str:
    """A dynamic fence keeps even source-supplied fences and HTML inside inert code."""
    fence = "`" * max(3, 1 + max((len(s) for s in re.findall(r"`+", text)), default=0))
    return f"{fence}text\n{text}\n{fence}\n"


def review_items(report: dict[str, Any], run_id: str) -> list[dict[str, str]]:
    items = []
    for mode in MODES:
        for case in sorted(report["modes"][mode]["cases"], key=lambda c: c["id"]):
            identity = encoded([run_id, case["id"], mode])
            items.append(
                {
                    "item_id": digest(identity),
                    "case_id": case["id"],
                    "mode": mode,
                    "category": case["category"] or "uncategorized",
                }
            )
    return items


def packet(
    dataset: EvaluationDataset, report: dict[str, Any], items: list[dict[str, str]]
) -> bytes:
    records = {
        (case["id"], mode): case
        for mode, result in report["modes"].items()
        for case in result["cases"]
    }
    parts = [RUBRIC]
    for index, item in enumerate(items, 1):
        record = records[item["case_id"], item["mode"]]
        answer = record["answer"]
        parts.extend(
            [
                f"\n### Item {index}\n",
                literal_block(f"item_id: {item['item_id']}\nmode: {item['mode']}"),
                "Question:\n",
                literal_block(record["query"]),
                "Actual response:\n",
                literal_block(f"status: {answer['status']}\n{answer['answer']}"),
            ]
        )
        for citation in answer["sources"]:
            document_id = report["document_labels"][citation["source_document_id"]]
            fields = {k: v for k, v in citation.items() if k != "excerpt"}
            fields["document_id"] = document_id
            parts.extend(
                [
                    "Citation identity and evidence pointer:\n",
                    literal_block(encoded(fields).decode().rstrip()),
                    "Original quotation:\n",
                    literal_block(citation["excerpt"]),
                ]
            )
    parts.append("\n## Complete original source corpus\n")
    for index, document in enumerate(dataset.documents, 1):
        parts.extend(
            [
                f"\n### Document {index}\n",
                literal_block(
                    f"document_id: {document.id}\ntitle: {document.title}\n"
                    f"full text range: [0, {len(document.text)})"
                ),
                literal_block(document.text),
            ]
        )
    return "\n".join(parts).encode()


def bundle_parts(raw_cases: bytes, raw_report: bytes) -> tuple[dict[str, bytes], dict[str, Any]]:
    dataset, report = checked_capture(raw_cases, raw_report)
    run_id = digest(encoded([digest(raw_cases), digest(raw_report)]))
    items = review_items(report, run_id)
    files = {
        "cases.json": raw_cases,
        "capture.json": raw_report,
        "packet.md": packet(dataset, report, items),
    }
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "files": {name: digest(raw) for name, raw in files.items()},
        "items": items,
    }
    files["manifest.json"] = encoded(manifest)
    files["judgments.json"] = encoded(
        {
            "schema_version": 1,
            "manifest_sha256": digest(files["manifest.json"]),
            "reviewer_id": "",
            "items": [
                {"item_id": item["item_id"], "verdict": None, "rationale": "", "evidence_spans": []}
                for item in items
            ],
        }
    )
    return files, manifest


def export_review(cases_path: Path, report_path: Path, output_dir: Path) -> dict[str, Any]:
    files, manifest = bundle_parts(cases_path.read_bytes(), report_path.read_bytes())
    output_dir.mkdir(parents=True, exist_ok=False)
    # A failed partial export has no complete manifest/inputs and cannot be summarized.
    for name, raw in files.items():
        (output_dir / name).write_bytes(raw)
    return manifest


def validate_judgment(
    row: Judgment, record: dict[str, Any], dataset: EvaluationDataset, labels: dict[str, str]
) -> None:
    documents = {doc.id: doc.text for doc in dataset.documents}
    spans = row.evidence_spans
    if len(set(spans)) != len(spans):
        raise ValueError("Duplicate evidence reference")
    for span in spans:
        content = documents.get(span.document_id)
        if (
            content is None
            or not 0 <= span.start_char < span.end_char <= len(content)
            or not content[span.start_char : span.end_char].strip()
        ):
            raise ValueError("Evidence pointer must select nonblank original text")
    verdict = row.verdict
    if verdict is None:
        return
    if not row.rationale.strip():
        raise ValueError("Submitted judgments require a rationale")
    abstained = record["answer"]["status"] == "insufficient_evidence"
    if verdict != "uncertain" and abstained != verdict.endswith("abstention"):
        raise ValueError("Verdict incompatible with response status")
    if verdict in ("fully_supported", "partially_supported"):
        if not spans or any(
            not any(
                labels[c["source_document_id"]] == span.document_id
                and c["start_char"] <= span.start_char < span.end_char <= c["end_char"]
                for c in record["answer"]["sources"]
            )
            for span in spans
        ):
            raise ValueError("Support references must lie inside displayed quotations")
    if verdict == "conflicting":
        if len(spans) < 2 or any(
            a.document_id == b.document_id
            and a.start_char < b.end_char
            and b.start_char < a.end_char
            for index, a in enumerate(spans)
            for b in spans[index + 1 :]
        ):
            raise ValueError("Conflict requires distinct non-overlapping opposing evidence")
    if verdict == "unjustified_abstention" and not spans:
        raise ValueError("Unjustified abstention requires corpus evidence")


def statistics(rows: list[Judgment]) -> dict[str, Any]:
    counts: Counter[str | None] = Counter(row.verdict for row in rows)
    numerator = counts["fully_supported"]
    denominator = sum(counts[label] for label in DETERMINATE_QUOTES)
    return {
        "total": len(rows),
        "pending": counts[None],
        "reviewed": len(rows) - counts[None],
        "uncertain": counts["uncertain"],
        "verdict_counts": {label: counts[label] for label in VERDICTS},
        "full_support_rate": {
            "numerator": numerator,
            "denominator": denominator,
            "value": numerator / denominator if denominator else None,
        },
    }


def summarize_review(bundle: Path, judgments_path: Path) -> dict[str, Any]:
    files, manifest = bundle_parts(
        (bundle / "cases.json").read_bytes(), (bundle / "capture.json").read_bytes()
    )
    # Rebuild immutable artifacts, not merely their stored hashes. Judgments remain editable.
    for name in ("manifest.json", "packet.md"):
        if (bundle / name).read_bytes() != files[name]:
            raise ValueError("Immutable review bundle changed")
    raw_judgments = judgments_path.read_bytes()
    form = Judgments.model_validate(load_json(raw_judgments))
    if form.manifest_sha256 != digest(files["manifest.json"]):
        raise ValueError("Judgments belong to a different review bundle")
    items = {item["item_id"]: item for item in manifest["items"]}
    if len(form.items) != len(items) or {row.item_id for row in form.items} != set(items):
        raise ValueError("Require each review item exactly once")
    if any(row.verdict is not None for row in form.items) and not form.reviewer_id.strip():
        raise ValueError("Submitted judgments require a reviewer identifier")
    dataset, report = checked_capture(files["cases.json"], files["capture.json"])
    records = {
        (case["id"], mode): case
        for mode, result in report["modes"].items()
        for case in result["cases"]
    }
    for row in form.items:
        item = items[row.item_id]
        validate_judgment(
            row, records[item["case_id"], item["mode"]], dataset, report["document_labels"]
        )
    overall = statistics(form.items)
    status = (
        "human_review_pending"
        if not overall["reviewed"]
        else "human_review_incomplete"
        if overall["pending"]
        else "human_review_complete"
    )
    return {
        "schema_version": 1,
        "status": status,
        "interpretation": "Human judgments, not factual truth or a quality release gate.",
        "reviewer_id": form.reviewer_id,
        "manifest_sha256": form.manifest_sha256,
        "judgments_sha256": digest(raw_judgments),
        "source_hashes": manifest["files"],
        "overall": overall,
        **{
            f"by_{key}": {
                value: statistics([row for row in form.items if items[row.item_id][key] == value])
                for value in sorted({item[key] for item in items.values()})
            }
            for key in ("mode", "category")
        },
        "follow_up_item_ids": [
            row.item_id
            for row in form.items
            if row.verdict
            in {"partially_supported", "unsupported", "conflicting", "unjustified_abstention"}
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export", help="Create a new offline review bundle")
    export.add_argument("--cases", type=Path, required=True)
    export.add_argument("--report", type=Path, required=True)
    export.add_argument("--output-dir", type=Path, required=True)
    summary = commands.add_parser("summarize", help="Summarize explicitly supplied human judgments")
    summary.add_argument("--bundle", type=Path, required=True)
    summary.add_argument("--judgments", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "export":
            manifest = export_review(args.cases, args.report, args.output_dir)
            result = {
                "schema_version": 1,
                "status": "human_review_pending",
                "items": len(manifest["items"]),
                "manifest_sha256": digest(encoded(manifest)),
            }
        else:
            result = summarize_review(args.bundle, args.judgments)
        print(encoded(result).decode(), end="")
    except Exception as exc:
        print(
            f"Support review incomplete ({type(exc).__name__}); check inputs and bundle.",
            file=sys.stderr,
        )
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
