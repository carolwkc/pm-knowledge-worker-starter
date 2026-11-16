from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from pmknowledge.schemas import SearchHit


@pytest.mark.integration
def test_http_default_enables_validated_selection_and_legacy_control_remains_available(
    database, client, workspace, identity
):
    from pmknowledge.auth import Principal
    from pmknowledge.retrieval import ask

    wid = UUID(workspace())
    for _ in range(2):
        client.post(
            f"/api/v1/workspaces/{wid}/sources",
            data={"title": "Synthetic"},
            files={"file": ("a.txt", b"Launch evidence.")},
        )
    response = client.post(f"/api/v1/workspaces/{wid}/ask", json={"question": "launch"})
    assert len(response.json()["sources"]) == 1
    with Session(database) as session:
        assert (
            len(
                ask(
                    session,
                    wid,
                    "launch",
                    5,
                    principal=Principal(identity.user_id),
                    answer_policy="legacy",
                ).sources
            )
            == 2
        )


@pytest.mark.integration
@pytest.mark.parametrize("mode", ["semantic", "hybrid"])
@pytest.mark.parametrize("cosine,expected", [(0.64, "insufficient_evidence"), (0.66, "grounded")])
def test_selected_api_uses_raw_cosine_once_without_lexical_overlap(
    database, workspace, identity, mode, cosine, expected
):
    from math import sqrt

    from fastapi.testclient import TestClient

    from pmknowledge.config import Settings
    from pmknowledge.main import create_app

    class Vectors:
        model_id = "selection-controlled-v1"
        queries = 0

        def embed_passages(self, texts):
            return [[cosine, sqrt(1 - cosine**2), *([0.0] * 382)] for _ in texts]

        def embed_query(self, query):
            self.queries += 1
            return [1.0, *([0.0] * 383)]

    wid = workspace()
    vectors = Vectors()
    app = create_app(
        Settings(
            database_url=database.url.render_as_string(hide_password=False), embeddings_enabled=True
        ),
        embedder=vectors,
    )
    with TestClient(app, headers=identity.headers) as c:
        assert (
            c.post(
                f"/api/v1/workspaces/{wid}/sources",
                data={"title": "Synthetic"},
                files={"file": ("a.txt", b"Mechanics restore equipment.")},
            ).status_code
            == 201
        )
        answer = c.post(
            f"/api/v1/workspaces/{wid}/ask",
            json={"question": "repair broken service", "mode": mode},
        ).json()
        assert answer["status"] == expected
        assert vectors.queries == 1


def hit(number, excerpt="Exact evidence."):
    return SearchHit(
        source_document_id=UUID(int=number),
        document_version_id=UUID(int=100 + number),
        chunk_id=UUID(int=200 + number),
        title="Synthetic",
        external_uri=None,
        ordinal=0,
        excerpt=excerpt,
        start_char=0,
        end_char=len(excerpt),
        score=0.99,
    )


@pytest.mark.parametrize("mode", ["keyword", "semantic", "hybrid"])
def test_selection_preserves_order_spans_and_deduplicates_exact_text(mode):
    from pmknowledge.answer_selection import Thresholds, select_evidence

    hits = [
        hit(1),
        hit(2),
        hit(3, "Complementary evidence."),
        hit(4, "Third evidence."),
        hit(5, "Fourth evidence."),
    ]
    result = select_evidence(
        hits, {"evid"}, {h.chunk_id: {"evid"} for h in hits}, {}, mode, 0.6, Thresholds(0.5, 0.7)
    )
    assert result == [hits[0], hits[2], hits[3]]
    assert result[0] is hits[0]


def test_lexical_boundary_uses_distinct_terms_and_requires_positive_overlap():
    from pmknowledge.answer_selection import Thresholds, select_evidence

    h = hit(1)
    args = ([h], {"a", "b"}, {h.chunk_id: {"a"}}, {}, "keyword", 0.6)
    assert select_evidence(*args, Thresholds(0.5, None)) == [h]
    assert select_evidence(*args, Thresholds(0.5001, None)) == []
    assert (
        select_evidence([h], {"x"}, {h.chunk_id: {"a"}}, {}, "keyword", 0.6, Thresholds(0, None))
        == []
    )
    assert select_evidence(
        [h], {"a"}, {h.chunk_id: {"a"}}, {}, "keyword", 0.6, Thresholds(1, None)
    ) == [h]


@pytest.mark.parametrize("mode", ["semantic", "hybrid"])
def test_cosine_is_an_alternative_to_lexical_overlap_and_respects_runtime_floor(mode):
    from pmknowledge.answer_selection import Thresholds, select_evidence

    h = hit(1)
    args = ([h], {"question"}, {h.chunk_id: {"paraphrase"}}, {h.chunk_id: 0.7}, mode)
    assert select_evidence(*args, 0.6, Thresholds(1, 0.7)) == [h]
    assert select_evidence(*args, 0.71, Thresholds(1, 0.7)) == []
    assert (
        select_evidence([h], {"question"}, {h.chunk_id: set()}, {}, mode, 0.6, Thresholds(1, 0.7))
        == []
    )  # high fusion score is not cosine
    assert (
        select_evidence(
            [h], set(), {h.chunk_id: {"paraphrase"}}, {h.chunk_id: 1}, mode, 0.6, Thresholds(0, 0.6)
        )
        == []
    )


@pytest.mark.integration
def test_postgres_lexemes_and_selected_http_equivalent_keep_unicode_evidence(
    database, client, workspace, identity
):
    from pmknowledge.answer_selection import english_lexemes
    from pmknowledge.auth import Principal
    from pmknowledge.retrieval import ask, search

    wid = UUID(workspace())
    content = "🚲 Résumé launches.\r\n\r\nOther material."
    client.post(
        f"/api/v1/workspaces/{wid}/sources",
        data={"title": "Synthetic"},
        files={"file": ("a.txt", content.encode())},
    )
    with Session(database) as session:
        assert english_lexemes(session, ["the and", "launch launching launch"]) == [
            set(),
            {"launch"},
        ]
        principal = Principal(identity.user_id)
        before = search(session, wid, "résumé launching", 1, principal=principal)
        answer = ask(
            session, wid, "résumé launching", 1, principal=principal, answer_policy="selected"
        )
        assert len(answer.sources) == 1
        c = answer.sources[0]
        assert content[c.start_char : c.end_char] == c.excerpt == "🚲 Résumé launches."
        assert c.citation == "1"
        assert before == search(session, wid, "résumé launching", 1, principal=principal)
        assert (
            ask(session, wid, "the and", 5, principal=principal, answer_policy="selected").sources
            == []
        )


@pytest.mark.integration
def test_selected_policy_obeys_limits_freshness_and_feedback_format(
    database, client, workspace, identity
):
    from pmknowledge.auth import Principal
    from pmknowledge.retrieval import ask

    wid = UUID(workspace())
    receipt = client.post(
        f"/api/v1/workspaces/{wid}/sources",
        data={"title": "Synthetic"},
        files={"file": ("a.txt", b"Launch evidence.\n\nLaunch facts.")},
    ).json()
    with Session(database) as session:
        answer = ask(
            session,
            wid,
            "launch",
            1,
            principal=Principal(identity.user_id),
            answer_policy="selected",
        )
    assert len(answer.sources) == 1
    response = client.post(
        f"/api/v1/workspaces/{wid}/feedback",
        json={
            "submission_id": str(UUID(int=599)),
            "question": "launch",
            "mode": "keyword",
            "answer": answer.model_dump(mode="json"),
            "rating": "helpful",
        },
    )
    assert response.status_code == 201
    client.post(
        f"/api/v1/workspaces/{wid}/sources/{receipt['source_document_id']}/versions",
        files={"file": ("a.txt", b"Replacement only.")},
    )
    with Session(database) as session:
        assert (
            ask(
                session,
                wid,
                "launch",
                5,
                principal=Principal(identity.user_id),
                answer_policy="selected",
            ).sources
            == []
        )


@pytest.mark.integration
@pytest.mark.parametrize("mode", ["semantic", "hybrid"])
def test_selected_denied_before_inference_and_disabled_mode_stays_explicit(
    database, workspace, identity, mode
):
    from fastapi import HTTPException

    from pmknowledge.auth import Principal
    from pmknowledge.embeddings import EmbeddingUnavailable
    from pmknowledge.retrieval import ask

    class Forbidden:
        model_id = "forbidden"

        def embed_query(self, question):
            raise AssertionError("denied request reached inference")

    wid = UUID(workspace())
    with Session(database) as session:
        with pytest.raises(HTTPException) as denied:
            ask(
                session,
                wid,
                "launch",
                5,
                principal=Principal(UUID(int=999)),
                mode=mode,
                embedder=Forbidden(),
                answer_policy="selected",
            )
        assert denied.value.status_code == 404
        with pytest.raises(EmbeddingUnavailable):
            ask(
                session,
                wid,
                "the and",
                5,
                principal=Principal(identity.user_id),
                mode=mode,
                answer_policy="selected",
            )
