import json
from hashlib import sha256
from pathlib import Path

import pytest


def metric(precision=0.6, recall=0.95, abstention=0.5, integrity=1):
    return {
        key: {"value": value}
        for key, value in {
            "evidence_precision": precision,
            "evidence_recall": recall,
            "negative_abstention": abstention,
            "citation_integrity": integrity,
        }.items()
    }


def test_gate_requires_per_mode_guards_and_strict_macro_improvement():
    from pmknowledge.selection_benchmark import release_gate

    baseline = {m: metric() for m in ("keyword", "semantic", "hybrid")}
    improved = {m: metric(0.7, 0.9, 0.7) for m in baseline}
    assert release_gate(baseline, improved) == []  # exactly five points allowed
    assert release_gate(baseline, baseline)  # equality is not improvement
    for field, value in [
        ("evidence_precision", 0.59),
        ("evidence_recall", 0.899),
        ("negative_abstention", 0.49),
        ("citation_integrity", 0.99),
        ("citation_integrity", None),
        ("evidence_precision", float("nan")),
        ("negative_abstention", float("inf")),
    ]:
        broken = json.loads(json.dumps(improved))
        broken["keyword"][field]["value"] = value
        assert release_gate(baseline, broken), field


def test_calibration_tiebreaks_favor_lower_thresholds_and_reject_missing_metrics():
    from pmknowledge.answer_selection import Thresholds
    from pmknowledge.selection_benchmark import calibration_key, eligible

    base = metric()
    assert eligible(base, metric(recall=0.9))
    assert not eligible(base, metric(recall=0.899))
    assert calibration_key([base], Thresholds(0.1, 0.65)) > calibration_key(
        [base], Thresholds(0.2, 0.7)
    )
    assert not eligible(base, metric(precision=None))


def test_validation_corpus_is_frozen_balanced_and_separate_from_development():
    from collections import Counter

    from pmknowledge.evaluation import EvaluationDataset

    manifest = json.loads(Path("docs/evaluations/task-011-validation-freeze.json").read_text())
    raw = Path(manifest["dataset"]).read_bytes()
    assert sha256(raw).hexdigest() == manifest["sha256"]
    dataset = EvaluationDataset.model_validate_json(raw)
    assert len(dataset.documents) == 20
    assert Counter(c.category for c in dataset.cases) == dict.fromkeys(
        ["lexical", "paraphrase", "multi_source", "missing_evidence"], 10
    )
    development = EvaluationDataset.model_validate_json(
        Path("apps/api/evaluation/pilot-cases.json").read_bytes()
    )
    assert not ({d.id for d in dataset.documents} & {d.id for d in development.documents})
    assert any("\r\n" in d.text and "🚲" in d.text for d in dataset.documents)


def test_runtime_thresholds_match_frozen_development_policy():
    from dataclasses import asdict

    from pmknowledge.answer_selection import POLICY_ID, THRESHOLDS

    frozen = json.loads(Path("docs/evaluations/task-011-policy.json").read_bytes())
    assert frozen["policy_id"] == POLICY_ID
    assert {m: asdict(t) for m, t in THRESHOLDS.items()} == {
        m: value["thresholds"] for m, value in frozen["calibration"].items()
    }


def test_recorded_development_calibration_reproduces_frozen_choice():
    from pmknowledge.evaluation import EvaluationDataset
    from pmknowledge.selection_benchmark import calibrate, checked_reports

    frozen = json.loads(Path("docs/evaluations/task-011-policy.json").read_bytes())
    raw = Path("apps/api/evaluation/pilot-cases.json").read_bytes()
    reports = []
    for name, digest in frozen["reports"].items():
        content = Path(name).read_bytes()
        assert sha256(content).hexdigest() == digest
        reports.append(json.loads(content))
    result = calibrate(checked_reports(reports, raw), EvaluationDataset.model_validate_json(raw))
    assert result["calibration"] == frozen["calibration"]


def test_benchmark_cli_redacts_invalid_input_and_refuses_validation_tuning(monkeypatch, capsys):
    import pmknowledge.selection_benchmark as module

    monkeypatch.setattr(
        "sys.argv",
        [
            "benchmark",
            "calibrate",
            "--cases",
            "apps/api/evaluation/task011-validation.json",
            "--reports",
            "docs/evaluations/task-011-validation-k5.json",
            "docs/evaluations/task-011-validation-k10.json",
        ],
    )
    with pytest.raises(SystemExit) as result:
        module.main()
    assert result.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "Selection benchmark incomplete (ValueError).\n"


def test_benchmark_cli_distinguishes_completed_failed_gate(monkeypatch, capsys):
    import pmknowledge.selection_benchmark as module

    monkeypatch.setattr(
        "sys.argv",
        [
            "benchmark",
            "validate",
            "--cases",
            "apps/api/evaluation/task011-validation.json",
            "--reports",
            "docs/evaluations/task-011-validation-k5.json",
            "docs/evaluations/task-011-validation-k10.json",
        ],
    )
    monkeypatch.setattr(module, "validate", lambda *_: {"passed": False, "failures": ["synthetic"]})
    with pytest.raises(SystemExit) as result:
        module.main()
    assert result.value.code == 1
    captured = capsys.readouterr()
    assert json.loads(captured.out)["failures"] == ["synthetic"]
    assert captured.err == ""


@pytest.mark.parametrize(
    "corruption",
    [
        "empty_cases",
        "duplicate_case",
        "mode_failed",
        "probe_failed",
        "case_failed",
        "fixture_failed",
        "metric_changed",
        "answer_changed",
        "source_changed",
    ],
)
def test_inconsistent_captures_cannot_green_light_release(corruption):
    from pmknowledge.selection_benchmark import checked_reports

    reports = [
        json.loads(Path(f"docs/evaluations/task-011-validation-k{k}.json").read_bytes())
        for k in (5, 10)
    ]
    mode = reports[0]["modes"]["keyword"]
    if corruption == "empty_cases":
        mode["cases"] = []
    if corruption == "duplicate_case":
        mode["cases"][1] = mode["cases"][0]
    if corruption == "mode_failed":
        mode["passed"] = False
    if corruption == "probe_failed":
        mode["probes"] = {"passed": False, "failures": ["leak"]}
    if corruption == "case_failed":
        mode["cases"][0]["failures"] = ["invalid_original_span"]
    if corruption == "fixture_failed":
        reports[0]["fixture_failures"] = ["corrupted source"]
    if corruption == "metric_changed":
        mode["policy_metrics"]["selected"]["evidence_precision"]["value"] = 1
    if corruption == "answer_changed":
        mode["cases"][0]["policy_answers"]["selected"]["answer"] += " Unsupported."
    if corruption == "source_changed":
        mode["cases"][0]["search_hits"][0]["excerpt"] = "Forged."
    with pytest.raises(ValueError):
        checked_reports(reports, Path("apps/api/evaluation/task011-validation.json").read_bytes())


@pytest.mark.parametrize("bad", ["failed", "wrong_hash", "missing_mode", "wrong_budget"])
def test_benchmark_rejects_incomplete_or_unmatched_report_inputs(bad):
    from pmknowledge.selection_benchmark import checked_reports

    raw = Path("apps/api/evaluation/pilot-cases.json").read_bytes()
    reports = [
        {
            "report_version": 3,
            "passed": True,
            "cases_sha256": sha256(raw).hexdigest(),
            "k": k,
            "modes": dict.fromkeys(["keyword", "semantic", "hybrid"], {}),
        }
        for k in (5, 10)
    ]
    if bad == "failed":
        reports[0]["passed"] = False
    if bad == "wrong_hash":
        reports[0]["cases_sha256"] = "wrong"
    if bad == "missing_mode":
        reports[0]["modes"] = {}
    if bad == "wrong_budget":
        reports[0]["k"] = 3
    with pytest.raises(ValueError):
        checked_reports(reports, raw)
