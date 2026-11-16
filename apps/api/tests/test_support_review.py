"""Offline human review contracts; test judgments are synthetic, never human findings."""

import copy
import json
from collections import Counter
from hashlib import sha256
from pathlib import Path

import pytest

CAPTURE = Path("docs/evaluations/task-011-validation-k5.json")
CASES = Path("apps/api/evaluation/task011-validation.json")


def read(path):
    return json.loads(path.read_bytes())


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def bundle(tmp_path):
    from pmknowledge.support_review import export_review

    target = tmp_path / "bundle"
    export_review(CASES, CAPTURE, target)
    return target


def records(bundle):
    report = read(bundle / "capture.json")
    return {
        (case["id"], mode): case
        for mode, result in report["modes"].items()
        for case in result["cases"]
    }


def pointer(bundle, item):
    report = read(bundle / "capture.json")
    citation = records(bundle)[item["case_id"], item["mode"]]["answer"]["sources"][0]
    return {
        "document_id": report["document_labels"][citation["source_document_id"]],
        "start_char": citation["start_char"],
        "end_char": citation["end_char"],
    }


def edited(bundle):
    form = read(bundle / "judgments.json")
    mapping = {item["item_id"]: item for item in read(bundle / "manifest.json")["items"]}
    form["reviewer_id"] = "synthetic-test-reviewer"
    grounded = [
        row
        for row in form["items"]
        if records(bundle)[mapping[row["item_id"]]["case_id"], mapping[row["item_id"]]["mode"]][
            "answer"
        ]["status"]
        == "grounded"
    ]
    return form, grounded, mapping


def test_fresh_corpus_is_balanced_frozen_and_not_old_validation():
    from pmknowledge.evaluation import EvaluationDataset

    path = Path("apps/api/evaluation/task012-review.json")
    raw = path.read_bytes()
    dataset = EvaluationDataset.model_validate_json(raw)
    freeze = read(Path("docs/evaluations/task-012-corpus-freeze.json"))
    assert freeze["dataset"] == str(path)
    assert freeze["sha256"] == sha256(raw).hexdigest()
    assert len(dataset.documents) == 12
    assert Counter(c.category for c in dataset.cases) == dict.fromkeys(
        ["direct_support", "multi_source", "missing_fact", "conflict_resolution"], 6
    )
    for old_path in [CASES, Path("apps/api/evaluation/pilot-cases.json")]:
        old = EvaluationDataset.model_validate_json(old_path.read_bytes())
        assert not {d.id for d in dataset.documents} & {d.id for d in old.documents}
        assert not {d.text for d in dataset.documents} & {d.text for d in old.documents}
    assert any("\r\n" in d.text and "🚡" in d.text for d in dataset.documents)
    for case in dataset.cases:
        if case.category in {"missing_fact", "conflict_resolution"}:
            assert case.evidence_spans == []
        elif case.category == "multi_source":
            assert len(case.relevant_document_ids) == 2
        else:
            assert case.evidence_spans


def test_export_preserves_inputs_is_deterministic_and_blank_is_pending(bundle, tmp_path):
    from pmknowledge.support_review import export_review, summarize_review

    other = tmp_path / "repeat"
    export_review(CASES, CAPTURE, other)
    assert {p.name for p in bundle.iterdir()} == {
        "cases.json",
        "capture.json",
        "packet.md",
        "manifest.json",
        "judgments.json",
    }
    for path in bundle.iterdir():
        assert path.read_bytes() == (other / path.name).read_bytes()
    assert (bundle / "cases.json").read_bytes() == CASES.read_bytes()
    assert (bundle / "capture.json").read_bytes() == CAPTURE.read_bytes()
    manifest = read(bundle / "manifest.json")
    assert len(manifest["items"]) == 120
    packet = (bundle / "packet.md").read_text()
    assert "policy_answers" not in packet
    assert "evidence_precision" not in packet
    assert "Gold" not in packet
    for document in read(CASES)["documents"]:
        assert document["text"].replace("\r\n", "\n") in packet
    summary = summarize_review(bundle, bundle / "judgments.json")
    assert summary["status"] == "human_review_pending"
    assert summary["overall"]["pending"] == 120
    assert summary["overall"]["reviewed"] == 0
    assert summary["overall"]["full_support_rate"] == {
        "numerator": 0,
        "denominator": 0,
        "value": None,
    }
    assert "passed" not in summary
    with pytest.raises(FileExistsError):
        export_review(CASES, CAPTURE, bundle)


@pytest.mark.parametrize(
    "corruption",
    ["hash", "mode", "k", "policy", "threshold", "floor", "model", "probe", "case", "fixture"],
)
def test_export_rejects_incomplete_or_wrong_policy_captures(tmp_path, corruption):
    from pmknowledge.support_review import export_review

    report = read(CAPTURE)
    if corruption == "hash":
        report["cases_sha256"] = "0" * 64
    elif corruption == "mode":
        del report["modes"]["semantic"]
    elif corruption == "k":
        report["k"] = 10
    elif corruption == "policy":
        report["answer_policy"] = "legacy"
    elif corruption == "threshold":
        report["settings"]["answer_selection"]["thresholds"]["keyword"]["lexical"] = 0.1
    elif corruption == "floor":
        report["semantic_min_score"] = 0.7
    elif corruption == "model":
        report["model_id"] = "different-model"
    elif corruption == "probe":
        report["modes"]["keyword"]["probes"]["passed"] = False
    elif corruption == "case":
        report["modes"]["keyword"]["cases"].pop()
    else:
        report["fixture_failures"] = [{"document_id": "broken"}]
    path = tmp_path / "report.json"
    write(path, report)
    with pytest.raises((ValueError, KeyError)):
        export_review(CASES, path, tmp_path / "rejected")
    assert not (tmp_path / "rejected").exists()


@pytest.mark.parametrize("filename", ["cases.json", "capture.json", "packet.md", "manifest.json"])
def test_summary_rejects_altered_bundle(bundle, filename):
    from pmknowledge.support_review import summarize_review

    path = bundle / filename
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError):
        summarize_review(bundle, bundle / "judgments.json")


@pytest.mark.parametrize(
    "corruption",
    [
        "missing",
        "duplicate",
        "unknown",
        "binding",
        "rationale",
        "reviewer",
        "span",
        "boolean_offset",
        "outside_quote",
        "conflict_one_position",
        "status",
        "verdict",
        "extra",
    ],
)
def test_summary_rejects_invalid_judgments(bundle, tmp_path, corruption):
    from pmknowledge.support_review import summarize_review

    form, grounded, mapping = edited(bundle)
    row = grounded[0]
    row.update(
        verdict="fully_supported",
        rationale="Synthetic test only.",
        evidence_spans=[pointer(bundle, mapping[row["item_id"]])],
    )
    if corruption == "missing":
        form["items"].pop()
    elif corruption == "duplicate":
        form["items"][1] = copy.deepcopy(form["items"][0])
    elif corruption == "unknown":
        form["items"][0]["item_id"] = "unknown"
    elif corruption == "binding":
        form["manifest_sha256"] = "0" * 64
    elif corruption == "rationale":
        row["rationale"] = "  "
    elif corruption == "reviewer":
        form["reviewer_id"] = ""
    elif corruption == "span":
        row["evidence_spans"][0]["end_char"] = 100000
    elif corruption == "boolean_offset":
        row["evidence_spans"][0]["start_char"] = False
    elif corruption == "outside_quote":
        span = row["evidence_spans"][0]
        doc = next(d for d in read(CASES)["documents"] if d["id"] == span["document_id"])
        span.update(start_char=0, end_char=len(doc["text"]))
    elif corruption == "conflict_one_position":
        row["verdict"] = "conflicting"
    elif corruption == "status":
        row["verdict"] = "justified_abstention"
    elif corruption == "verdict":
        row["verdict"] = "looks_good"
    else:
        row["untrusted"] = "extra field"
    path = tmp_path / "edited.json"
    write(path, form)
    with pytest.raises(ValueError):
        summarize_review(bundle, path)


def test_summary_counts_partial_reviews_uncertainty_and_denominators(bundle, tmp_path):
    from pmknowledge.support_review import summarize_review

    form, grounded, mapping = edited(bundle)
    for row, verdict in zip(
        grounded[:4],
        ["fully_supported", "partially_supported", "unsupported", "uncertain"],
        strict=True,
    ):
        row.update(verdict=verdict, rationale="Synthetic test only.")
        if verdict in {"fully_supported", "partially_supported"}:
            row["evidence_spans"] = [pointer(bundle, mapping[row["item_id"]])]
    path = tmp_path / "edited.json"
    write(path, form)
    summary = summarize_review(bundle, path)
    assert summary["status"] == "human_review_incomplete"
    assert summary["overall"]["reviewed"] == 4
    assert summary["overall"]["uncertain"] == 1
    assert summary["overall"]["full_support_rate"] == {
        "numerator": 1,
        "denominator": 3,
        "value": 1 / 3,
    }
    assert sum(s["reviewed"] for s in summary["by_mode"].values()) == 4
    assert sum(s["reviewed"] for s in summary["by_category"].values()) == 4
    assert {row["item_id"] for row in grounded[1:3]} == set(summary["follow_up_item_ids"])


def test_markdown_literal_blocks_cannot_execute_source_markup():
    from pmknowledge.support_review import literal_block

    hostile = "```\n<script>alert('synthetic')</script>\n[link](https://example.invalid)\n``````"
    rendered = literal_block(hostile)
    lines = rendered.splitlines()
    assert lines[0] == "```````text"
    assert lines[-1] == "```````"
    assert hostile in rendered


def test_omitted_corpus_evidence_can_establish_conflict_but_not_full_support(bundle, tmp_path):
    from pmknowledge.support_review import summarize_review

    form, grounded, mapping = edited(bundle)
    row = grounded[0]
    shown = pointer(bundle, mapping[row["item_id"]])
    record = records(bundle)[mapping[row["item_id"]]["case_id"], mapping[row["item_id"]]["mode"]]
    labels = read(bundle / "capture.json")["document_labels"]
    quoted_documents = {labels[c["source_document_id"]] for c in record["answer"]["sources"]}
    omitted = next(d for d in read(CASES)["documents"] if d["id"] not in quoted_documents)
    outside = {"document_id": omitted["id"], "start_char": 0, "end_char": len(omitted["text"])}
    row.update(
        verdict="conflicting",
        rationale="Synthetic opposing positions for validator test.",
        evidence_spans=[shown, outside],
    )
    path = tmp_path / "test-only.json"
    write(path, form)
    assert summarize_review(bundle, path)["overall"]["verdict_counts"]["conflicting"] == 1
    row["verdict"] = "fully_supported"
    write(path, form)
    with pytest.raises(ValueError, match="displayed quotations"):
        summarize_review(bundle, path)


def test_abstention_verdicts_require_status_and_support_when_unjustified(bundle, tmp_path):
    from pmknowledge.support_review import summarize_review

    form, grounded, mapping = edited(bundle)
    abstained = [row for row in form["items"] if row not in grounded]
    assert len(abstained) >= 2
    abstained[0].update(verdict="justified_abstention", rationale="Synthetic missing-fact test.")
    abstained[1].update(
        verdict="unjustified_abstention",
        rationale="Synthetic false-abstention test.",
        evidence_spans=[pointer(bundle, mapping[grounded[0]["item_id"]])],
    )
    path = tmp_path / "test-only.json"
    write(path, form)
    summary = summarize_review(bundle, path)
    assert summary["overall"]["verdict_counts"]["justified_abstention"] == 1
    assert summary["overall"]["verdict_counts"]["unjustified_abstention"] == 1
    assert summary["overall"]["full_support_rate"]["value"] is None
    abstained[1]["evidence_spans"] = []
    write(path, form)
    with pytest.raises(ValueError, match="requires corpus evidence"):
        summarize_review(bundle, path)


@pytest.mark.parametrize("malformed", [b'{"a": 1, "a": 2}', b'{"a": NaN}', b'{"a": Infinity}'])
def test_json_ambiguities_are_rejected(malformed):
    from pmknowledge.support_review import load_json

    with pytest.raises(ValueError):
        load_json(malformed)


def test_canonical_task012_bundle_is_review_ready_not_human_findings():
    from pmknowledge.support_review import summarize_review

    bundle = Path("docs/evaluations/task-012-review")
    summary = summarize_review(bundle, bundle / "judgments.json")
    assert summary["overall"]["total"] == 72
    assert summary["overall"]["pending"] == 72
    assert summary["reviewer_id"] == ""
    assert summary["status"] == "human_review_pending"
    assert {key: value["total"] for key, value in summary["by_category"].items()} == {
        "direct_support": 18,
        "multi_source": 18,
        "missing_fact": 18,
        "conflict_resolution": 18,
    }
    assert (bundle / "cases.json").read_bytes() == Path(
        "apps/api/evaluation/task012-review.json"
    ).read_bytes()


def test_cli_redacts_failures_and_exports_pending_summary(bundle, monkeypatch, capsys):
    from pmknowledge.support_review import main

    monkeypatch.setattr(
        "sys.argv",
        [
            "support_review",
            "summarize",
            "--bundle",
            str(bundle),
            "--judgments",
            str(bundle / "judgments.json"),
        ],
    )
    main()
    assert json.loads(capsys.readouterr().out)["status"] == "human_review_pending"
    monkeypatch.setattr(
        "sys.argv",
        [
            "support_review",
            "export",
            "--cases",
            "private-secret",
            "--report",
            str(CAPTURE),
            "--output-dir",
            "unused",
        ],
    )
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    result = capsys.readouterr()
    assert not result.out
    assert "private-secret" not in result.err


@pytest.mark.integration
def test_real_source_to_review_flow_and_fixture_rollback(database, tmp_path):
    from sqlalchemy.orm import Session
    from test_pilot_evaluation import ControlledEmbedder, counts, dataset

    from pmknowledge.embeddings import MODEL_ID
    from pmknowledge.evaluation import evaluate
    from pmknowledge.support_review import export_review, summarize_review

    encoder = ControlledEmbedder()
    encoder.model_id = MODEL_ID
    with Session(database) as session, session.begin():
        before = counts(session)
        report = evaluate(session, dataset(), encoder, k=5)
        assert counts(session) == before
    raw = dataset().model_dump_json().encode()
    report["cases_sha256"] = sha256(raw).hexdigest()
    cases_path, report_path = tmp_path / "cases.json", tmp_path / "capture.json"
    cases_path.write_bytes(raw)
    write(report_path, report)
    target = tmp_path / "bundle"
    export_review(cases_path, report_path, target)
    form, grounded, mapping = edited(target)
    for row in form["items"]:
        row["rationale"] = "Synthetic integration test, not a human judgment."
        row["verdict"] = "uncertain"
    grounded[0].update(
        verdict="fully_supported", evidence_spans=[pointer(target, mapping[grounded[0]["item_id"]])]
    )
    write(tmp_path / "test-only-judgments.json", form)
    summary = summarize_review(target, tmp_path / "test-only-judgments.json")
    assert summary["status"] == "human_review_complete"
    assert summary["overall"]["total"] == 6
    assert summary["overall"]["full_support_rate"]["value"] == 1
    assert read(target / "judgments.json")["reviewer_id"] == ""
