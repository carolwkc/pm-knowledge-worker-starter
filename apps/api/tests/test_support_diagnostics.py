"""AI diagnostic traces must not become human findings or answerability proofs."""

import copy
import json
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

import pytest

BUNDLE = Path("docs/evaluations/task-012-review")
REVIEW = Path("docs/evaluations/task-013-ai-review.json")


def read(path):
    return json.loads(path.read_bytes())


def diagnose(tmp_path, review=None, bundle=BUNDLE):
    from pmknowledge.support_diagnostics import export_diagnostics

    review_path = REVIEW
    if review is not None:
        review_path = tmp_path / "review.json"
        review_path.write_text(json.dumps(review), encoding="utf-8")
    output = tmp_path / "output"
    export_diagnostics(bundle, review_path, output)
    return read(output / "diagnostics.json")


def item(report, case, mode):
    return next(row for row in report["items"] if row["case_id"] == case and row["mode"] == mode)


def test_canonical_ai_review_counts_and_unchanged_human_bundle(tmp_path):
    before = {path.name: sha256(path.read_bytes()).hexdigest() for path in BUNDLE.iterdir()}
    report = diagnose(tmp_path)
    assert report["status"] == "ai_review_complete"
    assert report["review_kind"] == "ai"
    assert report["overall"]["total"] == 72
    assert report["overall"]["verdict_counts"] == {
        "fully_supported": 29,
        "partially_supported": 1,
        "unsupported": 24,
        "conflicting": 18,
        "justified_abstention": 0,
        "unjustified_abstention": 0,
        "uncertain": 0,
    }
    for mode, full, partial in [("keyword", 10, 0), ("semantic", 9, 1), ("hybrid", 10, 0)]:
        counts = report["by_mode"][mode]["verdict_counts"]
        assert (counts["fully_supported"], counts["partially_supported"]) == (full, partial)
        assert counts["unsupported"] == 8
        assert counts["conflicting"] == 6
    assert report["response_status_counts"] == {"grounded": 72}
    assert all(row["verdict"] is None for row in read(BUNDLE / "judgments.json")["items"])
    assert before == {path.name: sha256(path.read_bytes()).hexdigest() for path in BUNDLE.iterdir()}


def test_traces_distinguish_selection_gap_candidate_gap_and_missing_fact(tmp_path):
    report = diagnose(tmp_path)
    partial = item(report, "review012-multi-04", "semantic")
    escalation = next(
        t for t in partial["authored_support"] if t["document_id"] == "review012-pipitdock-b"
    )
    assert escalation["candidate_ranks"] == [5]
    assert escalation["emitted_citations"] == []
    assert "selection_gap" in partial["findings"]
    assert "candidate_gap" not in partial["findings"]
    for mode in ("keyword", "semantic", "hybrid"):
        gap = item(report, "review012-multi-05", mode)
        assert len(gap["authored_support"]) == 2
        assert all(t["candidate_ranks"] == [] for t in gap["authored_support"])
        assert "candidate_gap" in gap["findings"]
        assert "selection_gap" not in gap["findings"]
        missing = item(report, "review012-missing-03", mode)
        assert missing["authored_support"] == []
        assert missing["findings"] == ["missing_fact_grounded"]
    full = item(report, "review012-direct-01", "keyword")
    assert full["findings"] == []
    assert full["authored_support"][0]["candidate_ranks"] == [1]
    assert full["authored_support"][0]["emitted_citations"] == ["1"]
    conflict = item(report, "review012-conflict-01", "semantic")
    assert conflict["authored_support"] == []
    assert "unresolved_conflict_grounded" in conflict["findings"]
    assert conflict["ai_evidence"][0]["candidate_ranks"] == [3]
    assert conflict["ai_evidence"][1]["candidate_ranks"] == [4]
    assert conflict["ai_evidence"][1]["emitted_citations"] == []


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "duplicate",
        "unknown",
        "binding",
        "span",
        "status",
        "rationale",
        "review_kind",
        "pending",
        "rubric",
        "support_outside_quote",
        "reviewer",
        "date",
    ],
)
def test_rejects_invalid_reviews_before_creating_output(tmp_path, mutation):
    review = read(REVIEW)
    if mutation == "missing":
        review["items"].pop()
    elif mutation == "duplicate":
        review["items"][-1] = copy.deepcopy(review["items"][0])
    elif mutation == "unknown":
        review["items"][0]["item_id"] = "unknown"
    elif mutation == "binding":
        review["manifest_sha256"] = "0" * 64
    elif mutation == "span":
        review["items"][0]["evidence_spans"][0]["end_char"] = 999999
    elif mutation == "status":
        review["items"][0]["verdict"] = "justified_abstention"
    elif mutation == "rationale":
        review["items"][0]["rationale"] = "  "
    elif mutation == "review_kind":
        review["review_kind"] = "human"
    elif mutation == "pending":
        review["items"][0]["verdict"] = None
    elif mutation == "rubric":
        review["provenance"]["rubric_sha256"] = "0" * 64
    elif mutation == "support_outside_quote":
        row = next(r for r in review["items"] if r["verdict"] == "fully_supported")
        row["evidence_spans"] = [
            {"document_id": "review012-pipitdock-b", "start_char": 149, "end_char": 237}
        ]
    elif mutation == "date":
        review["provenance"]["review_date"] = "2026-99-99"
    else:
        review["reviewer_id"] = "  "
    with pytest.raises(ValueError):
        diagnose(tmp_path, review)
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize("filename", ["packet.md", "manifest.json", "capture.json", "cases.json"])
def test_rejects_tampered_bundle(tmp_path, filename):
    import shutil

    bundle = tmp_path / "bundle"
    shutil.copytree(BUNDLE, bundle)
    path = bundle / filename
    if filename.endswith(".json"):
        data = read(path)
        data["tampered"] = True
        path.write_text(json.dumps(data), encoding="utf-8")
    else:
        path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(ValueError):
        diagnose(tmp_path, bundle=bundle)
    assert not (tmp_path / "output").exists()


def test_deterministic_inert_report_original_offsets_and_no_overwrite(tmp_path):
    from pmknowledge.support_diagnostics import export_diagnostics

    review = read(REVIEW)
    review["items"][0]["rationale"] += (
        "\n``````\n<script>bad()</script>\n[link](https://example.invalid)"
    )
    report = diagnose(tmp_path, review)
    text = (tmp_path / "output" / "report.md").read_text()
    # The rationale's six backticks cannot close the longer literal fence.
    assert "```````text\n" in text
    assert "<script>bad()</script>" in text
    assert text.count("## Item ") == 72
    direct = item(report, "review012-direct-01", "keyword")["authored_support"][0]
    assert direct["text"] == "The Asterline relay supports 48 inspection lanes per gateway."
    assert direct["start_char"] == 178  # Original CRLF and emoji are counted as codepoints.
    other = tmp_path / "other"
    export_diagnostics(BUNDLE, tmp_path / "review.json", other)
    for name in ("diagnostics.json", "report.md"):
        assert (other / name).read_bytes() == (tmp_path / "output" / name).read_bytes()
    with pytest.raises(FileExistsError):
        export_diagnostics(BUNDLE, REVIEW, other)


@pytest.mark.parametrize(
    "raw", ['{"review_kind":"ai","review_kind":"human"}', '{"n":NaN}', "{broken"]
)
def test_cli_rejects_malformed_input_with_redacted_diagnostics(tmp_path, raw):
    path = tmp_path / "invalid.json"
    path.write_text(raw)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pmknowledge.support_diagnostics",
            "--bundle",
            str(BUNDLE),
            "--ai-review",
            str(path),
            "--output-dir",
            str(tmp_path / "output"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert raw not in result.stderr
    assert not (tmp_path / "output").exists()


def test_cli_and_canonical_artifacts_reproduce(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pmknowledge.support_diagnostics",
            "--bundle",
            str(BUNDLE),
            "--ai-review",
            str(REVIEW),
            "--output-dir",
            str(tmp_path / "output"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["status"] == "ai_review_complete"
    for name in ("diagnostics.json", "report.md"):
        assert (tmp_path / "output" / name).read_bytes() == (
            Path("docs/evaluations/task-013-diagnostics") / name
        ).read_bytes()


def test_other_valid_bundle_does_not_claim_task012_findings(tmp_path):
    from pmknowledge.support_review import export_review

    bundle = tmp_path / "different-bundle"
    export_review(
        Path("apps/api/evaluation/task011-validation.json"),
        Path("docs/evaluations/task-011-validation-k5.json"),
        bundle,
    )
    form = read(bundle / "judgments.json")
    provenance = read(REVIEW)["provenance"]
    form.update(review_kind="ai", provenance=provenance, reviewer_id="synthetic-test-ai")
    for row in form["items"]:
        row.update(verdict="uncertain", rationale="Synthetic test judgment, not a finding.")
    report = diagnose(tmp_path, form, bundle)
    assert report["overall"]["uncertain"] == report["overall"]["total"]
    assert report["overall"]["full_support_rate"]["value"] is None
    text = (tmp_path / "output" / "report.md").read_text()
    assert "multi-01 through multi-04" not in text
    assert "No fully supported AI judgments" in text


def test_case_names_never_escape_literal_blocks_in_recommendation_links(tmp_path):
    from pmknowledge.support_diagnostics import render_report

    report = diagnose(tmp_path)
    for row in report["items"]:
        row["case_id"] = "](#outside) <script>source_only()</script>"
    text = render_report(report).decode()
    prose = text.split("## Item ")[0]
    assert "<script>" not in prose
    assert "](#outside)" not in prose
    assert "<script>source_only()</script>" in text  # Retained as inert data inside item fences.


def test_no_runtime_connections_or_input_bundle_output(tmp_path, monkeypatch):
    import socket

    from sqlalchemy.engine import Engine

    from pmknowledge.support_diagnostics import export_diagnostics

    def forbidden(*args, **kwargs):
        raise AssertionError("Offline diagnostics attempted a connection")

    monkeypatch.setattr(Engine, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    assert diagnose(tmp_path)["overall"]["total"] == 72
    with pytest.raises(ValueError):
        export_diagnostics(BUNDLE, REVIEW, BUNDLE / "must-not-be-created")
    assert not (BUNDLE / "must-not-be-created").exists()
