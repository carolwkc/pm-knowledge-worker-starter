"""Calibrate on development captures, or gate frozen policies on validation captures."""

import argparse
import json
import sys
from dataclasses import asdict
from hashlib import sha256
from math import isfinite
from pathlib import Path
from typing import Any
from uuid import UUID

from pmknowledge.answer_selection import POLICY_ID, THRESHOLDS, Thresholds, select_evidence
from pmknowledge.evaluation import EvaluationCase, EvaluationDataset, answer_metrics, span_coverage
from pmknowledge.retrieval import compose_hits
from pmknowledge.schemas import AnswerRead, RetrievalMode, SearchHit

MODES: tuple[RetrievalMode, ...] = ("keyword", "semantic", "hybrid")
Metrics = dict[str, Any]
EPSILON = 1e-12


def eligible(baseline: Metrics, selected: Metrics) -> bool:
    for key, allowance in (
        ("evidence_precision", 0),
        ("negative_abstention", 0),
        ("evidence_recall", 0.05),
    ):
        old, new = baseline[key]["value"], selected[key]["value"]
        if (
            old is None
            or new is None
            or not isfinite(old)
            or not isfinite(new)
            or not 0 <= old <= 1
            or not 0 <= new <= 1
            or new + allowance + EPSILON < old
        ):
            return False
    return bool(selected["citation_integrity"]["value"] == 1)


def calibration_key(metrics: list[Metrics], thresholds: Thresholds) -> tuple[float, ...]:
    return (
        *[
            sum(float(m[key]["value"]) for m in metrics) / len(metrics)
            for key in ("evidence_precision", "negative_abstention", "evidence_recall")
        ],
        -thresholds.lexical,
        -(thresholds.cosine or 0),
    )


def release_gate(baseline: dict[str, Metrics], selected: dict[str, Metrics]) -> list[str]:
    failures = [
        f"{mode}: precision, abstention, recall or integrity guard failed"
        for mode in MODES
        if not eligible(baseline[mode], selected[mode])
    ]
    for key in ("evidence_precision", "negative_abstention"):
        old = [baseline[m][key]["value"] for m in MODES]
        new = [selected[m][key]["value"] for m in MODES]
        if any(v is None for v in old + new) or sum(new) <= sum(old) + EPSILON:
            failures.append(f"mean {key} did not improve")
    return failures


def checked_reports(reports: list[dict[str, Any]], raw_dataset: bytes) -> list[dict[str, Any]]:
    if len(reports) != 2 or {r["k"] for r in reports} != {5, 10}:
        raise ValueError("Require one capture each at k=5 and k=10")
    dataset = EvaluationDataset.model_validate_json(raw_dataset)
    for report in reports:
        if (
            report["report_version"] != 3
            or report["passed"] is not True
            or report["cases_sha256"] != sha256(raw_dataset).hexdigest()
            or set(report["modes"]) != set(MODES)
        ):
            raise ValueError("Require complete, passing three-mode captures of this dataset")
        check_capture(report, dataset)
    if any(
        reports[0].get(key) != reports[1].get(key)
        for key in ("model_id", "semantic_min_score", "runtime")
    ):
        raise ValueError("Captures must use the same model and settings")
    return sorted(reports, key=lambda report: report["k"])


def evidence_count(
    answer: AnswerRead,
    case: EvaluationCase,
    labels: dict[str, str],
) -> dict[str, int | None]:
    if case.evidence_spans is None:
        raise ValueError("Comparison requires complete support labels")
    relevant, covered = span_coverage(case.evidence_spans, answer.sources, labels)
    return {
        "emitted": len(answer.sources),
        "valid": len(answer.sources),
        "relevant": relevant,
        "covered": covered,
        "expected": len(case.evidence_spans),
    }


def check_capture(report: dict[str, Any], dataset: EvaluationDataset) -> None:
    """Reject incomplete/inconsistent exports; a top-level success flag is insufficient.

    This offline consistency check does not authenticate an operator's JSON file or
    replace the evaluator's independent database-backed permission/provenance audits.
    """
    cases = {case.id: case for case in dataset.cases}
    documents = {document.id: document for document in dataset.documents}
    labels = report["document_labels"]
    positives = sum(bool(case.relevant_document_ids) for case in dataset.cases)
    if (
        report["fixture_failures"] != []
        or report["documents"] != len(documents)
        or report["queries"] != len(cases)
        or report["positive_queries"] != positives
        or report["negative_queries"] != len(cases) - positives
        or len(labels) != len(documents)
        or set(labels.values()) != set(documents)
    ):
        raise ValueError("Inconsistent fixture or dataset coverage")
    for mode in MODES:
        result = report["modes"][mode]
        records = result["cases"]
        if (
            result["passed"] is not True
            or result["probes"]["passed"] is not True
            or result["probes"]["failures"] != []
            or len(records) != len(cases)
            or {record["id"] for record in records} != set(cases)
        ):
            raise ValueError("Incomplete cases or failed mode/probe integrity")
        rows: dict[str, list[dict[str, int | None]]] = {"legacy": [], "selected": []}
        for record in records:
            case = cases[record["id"]]
            if (
                record["failures"] != []
                or record["query"] != case.query
                or record["category"] != case.category
                or record["relevant"] != sorted(case.relevant_document_ids)
            ):
                raise ValueError("Inconsistent or failed case")
            hits = [SearchHit.model_validate(hit) for hit in record["search_hits"]]
            if len(hits) > report["k"] or len({hit.chunk_id for hit in hits}) != len(hits):
                raise ValueError("Duplicate or excess candidates")
            for hit in hits:
                document = documents[labels[str(hit.source_document_id)]]
                if (
                    not 0 <= hit.start_char < hit.end_char <= len(document.text)
                    or document.text[hit.start_char : hit.end_char] != hit.excerpt
                    or hit.title != document.title
                    or hit.external_uri is not None
                    or not isfinite(hit.score)
                ):
                    raise ValueError("Candidate does not match original fixture")
            inputs = record["selection_inputs"]
            thresholds = Thresholds(**report["settings"]["answer_selection"]["thresholds"][mode])
            paired = {
                "legacy": compose_hits(hits[:3]),
                "selected": compose_hits(
                    select_evidence(
                        hits,
                        set(inputs["question_lexemes"]),
                        {UUID(key): set(value) for key, value in inputs["excerpt_lexemes"].items()},
                        {UUID(key): value for key, value in inputs["cosine_scores"].items()},
                        mode,
                        report["semantic_min_score"],
                        thresholds,
                    )
                ),
            }
            for policy, answer in paired.items():
                if answer.model_dump(mode="json") != record["policy_answers"][policy]:
                    raise ValueError("Paired answer differs from captured candidates")
                rows[policy].append(evidence_count(answer, case, labels))
            policy = report["answer_policy"]
            if (
                record["answer"] != record["policy_answers"][policy]
                or record["evidence_counts"] != rows[policy][-1]
            ):
                raise ValueError("Inconsistent service answer or counts")
        recomputed = {policy: answer_metrics(counts) for policy, counts in rows.items()}
        if (
            result["policy_metrics"] != recomputed
            or result["answer_metrics"] != recomputed[report["answer_policy"]]
        ):
            raise ValueError("Stored metrics differ from captured evidence")


def replay_metrics(
    report: dict[str, Any],
    dataset: EvaluationDataset,
    mode: RetrievalMode,
    thresholds: Thresholds,
) -> Metrics:
    cases = {case.id: case for case in dataset.cases}
    rows: list[dict[str, int | None]] = []
    for record in report["modes"][mode]["cases"]:
        case = cases[record["id"]]
        if case.evidence_spans is None:
            raise ValueError("Calibration requires complete support labels")
        inputs = record["selection_inputs"]
        hits = [SearchHit.model_validate(hit) for hit in record["search_hits"]]
        answer = compose_hits(
            select_evidence(
                hits,
                set(inputs["question_lexemes"]),
                {UUID(key): set(value) for key, value in inputs["excerpt_lexemes"].items()},
                {UUID(key): value for key, value in inputs["cosine_scores"].items()},
                mode,
                report["semantic_min_score"],
                thresholds,
            )
        )
        rows.append(evidence_count(answer, case, report["document_labels"]))
    if len(rows) != len(cases):
        raise ValueError("Incomplete case capture")
    return answer_metrics(rows)


def calibrate(reports: list[dict[str, Any]], dataset: EvaluationDataset) -> dict[str, Any]:
    frozen: dict[str, Any] = {}
    for mode in MODES:
        options = []
        for lexical in (i / 20 for i in range(21)):
            cosines = [None] if mode == "keyword" else [i / 40 for i in range(24, 37)]
            for cosine in cosines:
                thresholds = Thresholds(lexical, cosine)
                metrics = [replay_metrics(report, dataset, mode, thresholds) for report in reports]
                if all(
                    eligible(report["modes"][mode]["policy_metrics"]["legacy"], result)
                    for report, result in zip(reports, metrics, strict=True)
                ):
                    options.append((calibration_key(metrics, thresholds), thresholds, metrics))
        if not options:
            raise ValueError(f"No development settings satisfy guards for {mode}")
        _, thresholds, metrics = max(options, key=lambda option: option[0])
        frozen[mode] = {
            "thresholds": asdict(thresholds),
            "budgets": {
                str(report["k"]): {
                    "legacy": report["modes"][mode]["policy_metrics"]["legacy"],
                    "selected": metrics[index],
                }
                for index, report in enumerate(reports)
            },
        }
    return {"policy_id": POLICY_ID, "calibration": frozen}


def validate(reports: list[dict[str, Any]], frozen: dict[str, Any]) -> dict[str, Any]:
    expected = {mode: frozen["calibration"][mode]["thresholds"] for mode in MODES}
    if frozen["policy_id"] != POLICY_ID or expected != {
        m: asdict(t) for m, t in THRESHOLDS.items()
    }:
        raise ValueError("Frozen policy does not match runtime")
    failures: list[str] = []
    budgets = {}
    for report in reports:
        if (
            report["answer_policy"] != "selected"
            or report["settings"]["answer_selection"]["thresholds"] != expected
        ):
            raise ValueError("Validation capture does not use the frozen policy")
        baseline: dict[str, Metrics] = {
            m: report["modes"][m]["policy_metrics"]["legacy"] for m in MODES
        }
        selected: dict[str, Metrics] = {
            m: report["modes"][m]["policy_metrics"]["selected"] for m in MODES
        }
        errors = release_gate(baseline, selected)
        failures.extend(f"k={report['k']}: {error}" for error in errors)
        budgets[str(report["k"])] = {"legacy": baseline, "selected": selected, "failures": errors}
    return {"passed": not failures, "failures": failures, "budgets": budgets}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("calibrate", "validate"))
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--reports", type=Path, nargs=2, required=True)
    parser.add_argument(
        "--freeze", type=Path, default=Path("docs/evaluations/task-011-policy.json")
    )
    args = parser.parse_args()
    try:
        raw = args.cases.read_bytes()
        report_bytes = [path.read_bytes() for path in args.reports]
        reports = checked_reports([json.loads(content) for content in report_bytes], raw)
        manifest = json.loads(Path("docs/evaluations/task-011-validation-freeze.json").read_bytes())
        if sha256(Path(manifest["dataset"]).read_bytes()).hexdigest() != manifest["sha256"]:
            raise ValueError("Validation corpus changed after freeze")
        if args.action == "calibrate":
            # The authored pilot is the only development input; validation labels are never tuned.
            development = Path("apps/api/evaluation/pilot-cases.json").read_bytes()
            if sha256(raw).hexdigest() != sha256(development).hexdigest():
                raise ValueError("Calibrate only on Task 010 development data")
            result = calibrate(reports, EvaluationDataset.model_validate_json(raw))
            result["validation_sha256"] = manifest["sha256"]
        else:
            frozen = json.loads(args.freeze.read_bytes())
            if sha256(raw).hexdigest() != frozen["validation_sha256"]:
                raise ValueError("Validate only the pre-frozen corpus")
            result = validate(reports, frozen)
        result["dataset_sha256"] = sha256(raw).hexdigest()
        result["reports"] = {
            str(path): sha256(content).hexdigest()
            for path, content in zip(args.reports, report_bytes, strict=True)
        }
        print(json.dumps(result, indent=2))
        if result.get("passed") is False:
            raise SystemExit(1)
    except Exception as exc:
        print(f"Selection benchmark incomplete ({type(exc).__name__}).", file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
