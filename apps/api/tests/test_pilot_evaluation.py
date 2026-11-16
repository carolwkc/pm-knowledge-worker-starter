"""Real PostgreSQL evaluation and independent evidence audit, with controlled vectors."""

import json
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from pmknowledge.evaluation import EvaluationDataset, evaluate
from pmknowledge.models import Base

pytestmark = pytest.mark.integration


class ControlledEmbedder:
    model_id = "pilot-controlled-v1"

    def embed_passages(self, texts):
        return [[1.0] + [0.0] * 383 for _ in texts]

    def embed_query(self, query):
        return [1.0] + [0.0] * 383


def dataset():
    return EvaluationDataset.model_validate(
        {
            "documents": [
                {
                    "id": "rocket",
                    "title": "Synthetic rocket",
                    "text": "🚀 Launch café.\r\n\r\nUnrelated distraction.",
                }
            ],
            "cases": [
                {
                    "id": "launch",
                    "query": "launch café",
                    "category": "lexical",
                    "relevant_document_ids": ["rocket"],
                    "evidence_spans": [{"document_id": "rocket", "start_char": 2, "end_char": 14}],
                },
                {
                    "id": "missing",
                    "query": "nonexistentplatypus",
                    "category": "missing_evidence",
                    "relevant_document_ids": [],
                    "evidence_spans": [],
                },
            ],
        }
    )


def counts(session):
    from sqlalchemy import func

    return {
        t.name: session.scalar(select(func.count()).select_from(t))
        for t in Base.metadata.sorted_tables
    }


@pytest.mark.parametrize("modes", [("keyword",), ("keyword", "semantic", "hybrid")])
def test_pilot_runs_actual_answers_and_rolls_back_all_rows(database, modes):
    with Session(database) as session, session.begin():
        before = counts(session)
        report = evaluate(
            session,
            dataset(),
            ControlledEmbedder() if len(modes) > 1 else None,
            k=10,
            selected_modes=modes,
        )
        assert counts(session) == before
    assert report["passed"] is True
    assert set(report["modes"]) == set(modes)
    keyword = report["modes"]["keyword"]
    assert keyword["answer_metrics"]["evidence_recall"]["value"] == 1
    assert keyword["answer_metrics"]["evidence_precision"]["value"] == 1
    assert keyword["answer_metrics"]["citation_integrity"]["value"] == 1
    assert keyword["probes"]["passed"] is True
    citation = keyword["cases"][0]["answer"]["sources"][0]
    assert citation["excerpt"] == "🚀 Launch café."
    assert keyword["cases"][1]["answer"]["status"] == "insufficient_evidence"


@pytest.mark.parametrize("phase", ["ingest", "query"])
def test_evaluation_failure_cleans_up_and_preserves_unrelated_rows(database, workspace, phase):
    workspace_id = workspace()

    class Interrupted(ControlledEmbedder):
        def embed_passages(self, texts):
            if phase == "ingest":
                raise RuntimeError("synthetic interrupted ingest")
            return super().embed_passages(texts)

        def embed_query(self, query):
            raise RuntimeError("synthetic interrupted query")

    with Session(database) as session, session.begin():
        before = counts(session)
        with pytest.raises(RuntimeError, match="synthetic interrupted"):
            evaluate(session, dataset(), Interrupted())
        assert counts(session) == before
        from pmknowledge.models import Workspace

        assert session.get(Workspace, UUID(workspace_id)) is not None


def test_independent_audit_rejects_every_forged_citation_field(
    database, workspace, client, identity
):
    from pmknowledge.auth import Principal
    from pmknowledge.evaluation_checks import audit_answer
    from pmknowledge.retrieval import ask

    workspace_id = UUID(workspace())
    client.post(
        f"/api/v1/workspaces/{workspace_id}/sources",
        data={"title": "Synthetic"},
        files={"file": ("a.txt", b"Launch evidence.")},
    )
    with Session(database) as session:
        principal = Principal(identity.user_id)
        answer = ask(session, workspace_id, "launch", 10, principal=principal)
        assert audit_answer(session, workspace_id, answer, principal) == ([], [[]])
        source = answer.sources[0]
        for field, value in {
            "title": "Forged",
            "external_uri": "https://example.invalid/forged",
            "ordinal": 99,
            "start_char": 1,
            "end_char": 99,
            "excerpt": "Forged",
            "source_document_id": UUID(int=1),
            "document_version_id": UUID(int=1),
            "chunk_id": UUID(int=1),
            "citation": "2",
        }.items():
            forged = answer.model_copy(
                update={"sources": [source.model_copy(update={field: value})]}
            )
            errors, citations = audit_answer(session, workspace_id, forged, principal)
            assert errors or citations[0], field
        for update in [
            {"answer": answer.answer + " Unsupported claim."},
            {"status": "insufficient_evidence"},
            {"sources": answer.sources * 2},
        ]:
            assert audit_answer(session, workspace_id, answer.model_copy(update=update), principal)[
                0
            ]


def test_integrity_failure_is_reported_even_when_quality_scores_are_high(database, monkeypatch):
    import pmknowledge.evaluation as module

    original = module.ask

    def forged(*args, **kwargs):
        result = original(*args, **kwargs)
        return result.model_copy(update={"answer": result.answer + " Unsupported claim."})

    monkeypatch.setattr(module, "ask", forged)
    with Session(database) as session:
        report = evaluate(session, dataset(), None, selected_modes=("keyword",))
    assert report["passed"] is False
    assert report["modes"]["keyword"]["cases"][0]["failures"]


def test_keyword_cli_never_constructs_model_and_prints_json(
    database, monkeypatch, tmp_path, capsys
):
    import pmknowledge.evaluation as module

    path = tmp_path / "synthetic.json"
    path.write_text(dataset().model_dump_json())
    monkeypatch.setenv("DATABASE_URL", database.url.render_as_string(hide_password=False))
    monkeypatch.setattr("sys.argv", ["evaluation", "--cases", str(path), "--modes", "keyword"])

    def forbidden(*args):
        raise AssertionError("keyword tried to load a model")

    monkeypatch.setattr(module, "LocalEmbedder", forbidden)
    module.main()
    report = json.loads(capsys.readouterr().out)
    assert report["passed"] is True
    assert report["cases_sha256"]
    assert report["model_id"] is None


def test_legacy_dataset_has_null_span_metrics(database):
    from pathlib import Path

    legacy = EvaluationDataset.model_validate_json(
        Path("apps/api/evaluation/cases.json").read_bytes()
    )
    with Session(database) as session:
        report = evaluate(session, legacy, None, selected_modes=("keyword",))
    assert report["modes"]["keyword"]["answer_metrics"]["evidence_precision"]["value"] is None


def test_selected_report_pairs_same_candidates_with_legacy_and_records_policy(database):
    from pmknowledge.answer_selection import THRESHOLDS
    from pmknowledge.selection_benchmark import replay_metrics

    with Session(database) as session:
        report = evaluate(
            session, dataset(), None, k=5, selected_modes=("keyword",), answer_policy="selected"
        )
    assert report["report_version"] == 3
    assert report["answer_policy"] == "selected"
    assert report["settings"]["answer_selection"]["policy_id"]
    mode = report["modes"]["keyword"]
    assert mode["answer_metrics"] == mode["policy_metrics"]["selected"]
    for case in mode["cases"]:
        assert case["answer"] == case["policy_answers"]["selected"]
        assert case["policy_answers"]["legacy"]["sources"] == [
            {**hit, "citation": str(i)}
            for i, hit in enumerate(
                [{k: v for k, v in h.items() if k != "score"} for h in case["search_hits"][:3]], 1
            )
        ]
        assert "question_lexemes" in case["selection_inputs"]
        assert len(case["search_hits"]) <= 5
    assert report["passed"]
    assert (
        replay_metrics(report, dataset(), "keyword", THRESHOLDS["keyword"])
        == mode["answer_metrics"]
    )


def test_selected_keyword_cli_does_not_load_model(database, monkeypatch, tmp_path, capsys):
    import pmknowledge.evaluation as module

    path = tmp_path / "synthetic.json"
    path.write_text(dataset().model_dump_json())
    monkeypatch.setenv("DATABASE_URL", database.url.render_as_string(hide_password=False))
    monkeypatch.setattr(
        "sys.argv",
        ["evaluation", "--cases", str(path), "--modes", "keyword", "--answer-policy", "selected"],
    )
    monkeypatch.setattr(module, "LocalEmbedder", lambda _: pytest.fail("unexpected model"))
    module.main()
    assert json.loads(capsys.readouterr().out)["answer_policy"] == "selected"


@pytest.mark.parametrize("failure", ["model", "integrity", "configuration"])
def test_cli_failure_status_and_redacted_diagnostics(
    database, monkeypatch, tmp_path, capsys, failure
):
    import pmknowledge.evaluation as module
    from pmknowledge.embeddings import EmbeddingUnavailable

    path = tmp_path / "synthetic.json"
    path.write_text(dataset().model_dump_json())
    monkeypatch.setenv("DATABASE_URL", database.url.render_as_string(hide_password=False))
    monkeypatch.setattr("sys.argv", ["evaluation", "--cases", str(path), "--modes", "semantic"])
    if failure == "model":

        class Missing(ControlledEmbedder):
            def embed_passages(self, texts):
                raise EmbeddingUnavailable("private synthetic secret not for stderr")

        monkeypatch.setattr(module, "LocalEmbedder", lambda _: Missing())
    elif failure == "configuration":
        monkeypatch.setenv("DATABASE_URL", "invalid-private-secret")
    else:
        monkeypatch.setattr(module, "evaluate", lambda *a, **kw: {"passed": False})
    with pytest.raises(SystemExit) as result:
        module.main()
    assert result.value.code == (1 if failure == "integrity" else 2)
    captured = capsys.readouterr()
    assert "private" not in captured.err
    assert "secret" not in captured.err
    if failure == "integrity":
        assert json.loads(captured.out)["passed"] is False
    else:
        assert captured.out == ""
        assert "Evaluation incomplete" in captured.err


def test_foreign_and_historical_evidence_fail_independent_audit(
    database, workspace, client, identity, identity_factory
):
    from pmknowledge.auth import Principal
    from pmknowledge.evaluation_checks import audit_answer
    from pmknowledge.retrieval import ask

    own = UUID(workspace())
    principal = Principal(identity.user_id)
    other = identity_factory()
    foreign = UUID(workspace(headers=other.headers))
    receipt = client.post(
        f"/api/v1/workspaces/{own}/sources",
        data={"title": "Synthetic"},
        files={"file": ("a.txt", b"Launch evidence.")},
    ).json()
    with Session(database) as session:
        answer = ask(session, own, "launch", 10, principal=principal)
        assert audit_answer(session, foreign, answer, principal)[1][0]
    client.post(
        f"/api/v1/workspaces/{own}/sources/{receipt['source_document_id']}/versions",
        files={"file": ("a.txt", b"Replacement evidence.")},
    )
    with Session(database) as session:
        assert "superseded_version" in audit_answer(session, own, answer, principal)[1][0]


def test_probe_failure_fails_overall_report(database, monkeypatch):
    import pmknowledge.evaluation_checks as checks

    original = checks.search

    def forged(*args, **kwargs):
        hits = original(*args, **kwargs)
        return [hit.model_copy(update={"document_version_id": UUID(int=1)}) for hit in hits]

    monkeypatch.setattr(checks, "search", forged)
    with Session(database) as session:
        report = evaluate(session, dataset(), None, selected_modes=("keyword",))
    assert report["passed"] is False
    assert "leaked_or_superseded_probe" in report["modes"]["keyword"]["probes"]["failures"]


@pytest.mark.parametrize("corruption", ["text", "title"])
def test_ingestion_cannot_redefine_authored_gold_evidence(database, monkeypatch, corruption):
    from io import BytesIO

    from fastapi import UploadFile

    import pmknowledge.evaluation as module

    original = module.ingest

    def corrupt(session, workspace_id, upload, **kwargs):
        if corruption == "text":
            # Equal-length replacement preserves gold offsets, exposing circular validation.
            upload = UploadFile(
                file=BytesIO(upload.file.read().replace(b"Launch", b"Bogusx")),
                filename=upload.filename,
            )
        else:
            kwargs["title"] = "Corrupted synthetic title"
        return original(session, workspace_id, upload, **kwargs)

    monkeypatch.setattr(module, "ingest", corrupt)
    with Session(database) as session, session.begin():
        before = counts(session)
        report = evaluate(session, dataset(), None, selected_modes=("keyword",))
        assert counts(session) == before
    assert report["passed"] is False
    assert report["fixture_failures"][0]["document_id"] == "rocket"
    assert report["modes"]["keyword"]["answer_metrics"]["evidence_precision"]["value"] == 0
