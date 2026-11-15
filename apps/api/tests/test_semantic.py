"""Controlled vectors test database/ranking correctness, not model quality."""

from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from pmknowledge.config import Settings
from pmknowledge.main import create_app

pytestmark = pytest.mark.integration


def vector(*values):
    return [*values, *([0.0] * (384 - len(values)))]


class FixtureEmbedder:
    model_id = "controlled-test-v1"

    def embed_passages(self, texts):
        vectors = {
            "Quasar diagnosis keyword.": vector(1.0, 0.0),
            "Engineers restore service by finding the failing component.": vector(0.0, 1.0),
            "Current workflow.": vector(0.0, 0.0, 1.0),
        }
        return [vectors.get(content, vector(0.0, 1.0)) for content in texts]

    def embed_query(self, query):
        return vector(0.0, 1.0)


@pytest.fixture
def semantic_client(database, identity):
    app = create_app(
        Settings(
            database_url=database.url.render_as_string(hide_password=False), embeddings_enabled=True
        ),
        embedder=FixtureEmbedder(),
    )
    with TestClient(app, headers=identity.headers) as client:
        yield client


def upload(client, workspace_id, content, source_id=None):
    url = f"/api/v1/workspaces/{workspace_id}/sources"
    if source_id:
        url += f"/{source_id}/versions"
    return client.post(
        url,
        files={"file": ("synthetic.txt", content.encode(), "text/plain")},
        data={"title": "Synthetic evidence"} if not source_id else {},
    )


def test_semantic_paraphrase_and_hybrid_keep_exact_citations(semantic_client, workspace):
    workspace_id = workspace()
    keyword = upload(semantic_client, workspace_id, "Quasar diagnosis keyword.").json()
    semantic_text = "Engineers restore service by finding the failing component."
    semantic = upload(semantic_client, workspace_id, semantic_text).json()
    url = f"/api/v1/workspaces/{workspace_id}"
    lexical_hits = semantic_client.get(f"{url}/search", params={"q": "quasar"}).json()["results"]
    assert [h["source_document_id"] for h in lexical_hits] == [keyword["source_document_id"]]
    hits = semantic_client.get(f"{url}/search", params={"q": "quasar", "mode": "semantic"}).json()[
        "results"
    ]
    assert [h["source_document_id"] for h in hits] == [semantic["source_document_id"]]
    assert hits[0]["excerpt"] == semantic_text
    hybrid = semantic_client.get(f"{url}/search", params={"q": "quasar", "mode": "hybrid"}).json()[
        "results"
    ]
    assert {h["source_document_id"] for h in hybrid} == {
        keyword["source_document_id"],
        semantic["source_document_id"],
    }
    answer = semantic_client.post(
        f"{url}/ask", json={"question": "repair the service", "mode": "semantic"}
    ).json()
    assert answer["status"] == "grounded"
    assert answer["sources"][0]["chunk_id"] == hits[0]["chunk_id"]
    assert f'[1] "{semantic_text}"' in answer["answer"]


@pytest.mark.parametrize("mode", ["semantic", "hybrid"])
def test_vector_retrieval_is_workspace_scoped_before_ranking(semantic_client, workspace, mode):
    owner, stranger = workspace(), workspace()
    upload(semantic_client, owner, "Engineers restore service by finding the failing component.")
    url = f"/api/v1/workspaces/{stranger}"
    assert (
        semantic_client.get(f"{url}/search", params={"q": "restore service", "mode": mode}).json()[
            "results"
        ]
        == []
    )
    answer = semantic_client.post(
        f"{url}/ask", json={"question": "restore service", "mode": mode}
    ).json()
    assert answer["status"] == "insufficient_evidence"
    assert answer["sources"] == []


def test_superseded_embeddings_are_excluded_and_duplicates_are_idempotent(
    semantic_client, workspace, database
):
    workspace_id = workspace()
    content = "Engineers restore service by finding the failing component."
    original = upload(semantic_client, workspace_id, content).json()
    source_id = original["source_document_id"]
    assert upload(semantic_client, workspace_id, content, source_id).json()["duplicate"] is True
    with database.connect() as connection:
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM chunk_embedding e JOIN source_chunk c ON c.id=e.chunk_id "
                    "WHERE c.document_version_id=:id"
                ),
                {"id": UUID(original["document_version_id"])},
            )
            == 1
        )
    upload(semantic_client, workspace_id, "Current workflow.", source_id)
    hits = semantic_client.get(
        f"/api/v1/workspaces/{workspace_id}/search",
        params={"q": "repair the service", "mode": "semantic"},
    ).json()["results"]
    assert hits == []


@pytest.mark.parametrize("mode", ["semantic", "hybrid"])
def test_disabled_semantic_mode_is_explicit_service_unavailable(client, workspace, mode):
    url = f"/api/v1/workspaces/{workspace()}"
    assert client.get(f"{url}/search", params={"q": "repair", "mode": mode}).status_code == 503
    assert client.post(f"{url}/ask", json={"question": "repair", "mode": mode}).status_code == 503


def test_invalid_mode_is_rejected(client, workspace):
    url = f"/api/v1/workspaces/{workspace()}"
    assert client.get(f"{url}/search", params={"q": "repair", "mode": "unknown"}).status_code == 422
    assert (
        client.post(f"{url}/ask", json={"question": "repair", "mode": "unknown"}).status_code == 422
    )


def test_backfill_is_workspace_scoped_and_repeatable(client, workspace, database):
    from sqlalchemy.orm import Session

    from pmknowledge.embeddings import backfill_workspace

    owner, stranger = workspace(), workspace()
    upload(client, owner, "Engineers restore service by finding the failing component.")
    upload(client, stranger, "Engineers restore service by finding the failing component.")
    with Session(database) as session, session.begin():
        assert backfill_workspace(session, UUID(owner), FixtureEmbedder()) == 1
    with Session(database) as session, session.begin():
        assert backfill_workspace(session, UUID(owner), FixtureEmbedder()) == 0
    with database.connect() as connection:
        rows = (
            connection.execute(
                text(
                    "SELECT d.workspace_id FROM chunk_embedding e "
                    "JOIN source_chunk c ON c.id=e.chunk_id "
                    "JOIN document_version v ON v.id=c.document_version_id "
                    "JOIN source_document d ON d.id=v.source_document_id "
                    "WHERE d.workspace_id IN (:owner,:stranger)"
                ),
                {"owner": UUID(owner), "stranger": UUID(stranger)},
            )
            .scalars()
            .all()
        )
    assert rows == [UUID(owner)]


def test_missing_local_model_returns_safe_error_and_rolls_back_ingestion(
    database, workspace, tmp_path, monkeypatch, identity
):
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    workspace_id = workspace()
    app = create_app(
        Settings(
            database_url=database.url.render_as_string(hide_password=False),
            embeddings_enabled=True,
            embedding_cache_dir=str(tmp_path / "missing-cache"),
        )
    )
    with TestClient(app, headers=identity.headers) as client:
        response = upload(client, workspace_id, "Private synthetic payload marker.")
        assert response.status_code == 503
        assert "Private synthetic payload marker" not in response.text
        # Keyword requests remain available, and the failed ingest created no source.
        assert (
            client.get(
                f"/api/v1/workspaces/{workspace_id}/search", params={"q": "synthetic"}
            ).json()["results"]
            == []
        )
    with database.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT count(*) FROM source_document WHERE workspace_id=:id"),
                {"id": UUID(workspace_id)},
            )
            == 0
        )


@pytest.mark.parametrize("bad_vector", [[], [float("nan")] * 384, [0.0] * 384])
def test_invalid_query_vectors_are_rejected_without_database_errors(
    database, workspace, bad_vector, identity
):
    class BrokenEmbedder(FixtureEmbedder):
        def embed_query(self, query):
            return bad_vector

    app = create_app(
        Settings(
            database_url=database.url.render_as_string(hide_password=False), embeddings_enabled=True
        ),
        embedder=BrokenEmbedder(),
    )
    with TestClient(app, headers=identity.headers) as client:
        response = client.get(
            f"/api/v1/workspaces/{workspace()}/search", params={"q": "query", "mode": "semantic"}
        )
        assert response.status_code == 503


def test_threshold_rejects_irrelevant_vectors(semantic_client, workspace):
    workspace_id = workspace()
    upload(semantic_client, workspace_id, "Quasar diagnosis keyword.")
    answer = semantic_client.post(
        f"/api/v1/workspaces/{workspace_id}/ask",
        json={"question": "completely different meaning", "mode": "semantic"},
    ).json()
    assert answer["status"] == "insufficient_evidence"
    assert answer["sources"] == []


def test_foreign_model_embeddings_do_not_enter_results(semantic_client, workspace, database):
    workspace_id = workspace()
    upload(
        semantic_client, workspace_id, "Engineers restore service by finding the failing component."
    )
    with database.begin() as connection:
        connection.execute(
            text(
                "UPDATE chunk_embedding SET model_id='other-model' WHERE chunk_id IN "
                "(SELECT c.id FROM source_chunk c "
                "JOIN document_version v ON v.id=c.document_version_id "
                "JOIN source_document d ON d.id=v.source_document_id WHERE d.workspace_id=:id)"
            ),
            {"id": UUID(workspace_id)},
        )
    assert (
        semantic_client.get(
            f"/api/v1/workspaces/{workspace_id}/search", params={"q": "repair", "mode": "semantic"}
        ).json()["results"]
        == []
    )


def test_hybrid_deduplicates_and_honors_limit(semantic_client, workspace):
    workspace_id = workspace()
    upload(
        semantic_client, workspace_id, "Engineers restore service by finding the failing component."
    )
    upload(semantic_client, workspace_id, "Another service note.")
    url = f"/api/v1/workspaces/{workspace_id}/search"
    first = semantic_client.get(url, params={"q": "service", "mode": "hybrid"}).json()["results"]
    assert len(first) == len({hit["chunk_id"] for hit in first}) == 2
    assert (
        first
        == semantic_client.get(url, params={"q": "service", "mode": "hybrid"}).json()["results"]
    )
    limited = semantic_client.get(
        url, params={"q": "service", "mode": "hybrid", "limit": 1}
    ).json()["results"]
    assert limited == first[:1]


def test_evaluation_leaves_no_fixture_data(database):
    from sqlalchemy.orm import Session

    from pmknowledge.evaluation import EvaluationDataset, evaluate

    dataset = EvaluationDataset.model_validate(
        {
            "documents": [{"id": "synthetic", "title": "Synthetic", "text": "Current workflow."}],
            "cases": [
                {"id": "question", "query": "workflow", "relevant_document_ids": ["synthetic"]}
            ],
        }
    )
    with database.connect() as connection:
        before = connection.scalar(text("SELECT count(*) FROM workspace"))
        users_before = connection.scalar(text("SELECT count(*) FROM app_user"))
        memberships_before = connection.scalar(text("SELECT count(*) FROM workspace_membership"))
    with Session(database) as session, session.begin():
        report = evaluate(session, dataset, FixtureEmbedder())
        assert report["modes"]["keyword"]["recall_at_k"] == 1.0
    with database.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM workspace")) == before
        assert connection.scalar(text("SELECT count(*) FROM app_user")) == users_before
        assert (
            connection.scalar(text("SELECT count(*) FROM workspace_membership"))
            == memberships_before
        )


def test_backfill_batches_and_rolls_back_when_a_later_inference_batch_fails(
    client, workspace, database
):
    from sqlalchemy.orm import Session

    from pmknowledge.embeddings import EmbeddingUnavailable, backfill_workspace

    class InterruptedEmbedder(FixtureEmbedder):
        def __init__(self):
            self.batches = 0

        def embed_passages(self, texts):
            self.batches += 1
            if self.batches > 1:
                raise EmbeddingUnavailable("Synthetic inference interruption")
            return super().embed_passages(texts)

    workspace_id = workspace()
    receipt = upload(client, workspace_id, "\n\n".join(["Synthetic evidence."] * 65)).json()
    assert receipt["chunk_count"] == 65
    with pytest.raises(EmbeddingUnavailable):
        with Session(database) as session, session.begin():
            backfill_workspace(session, UUID(workspace_id), InterruptedEmbedder())
    with database.connect() as connection:
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM chunk_embedding e JOIN source_chunk c ON c.id=e.chunk_id "
                    "WHERE c.document_version_id=:id"
                ),
                {"id": UUID(receipt["document_version_id"])},
            )
            == 0
        )


@pytest.mark.parametrize("mode", ["keyword", "semantic", "hybrid"])
def test_authorized_candidates_are_selected_before_ranking_and_limit(
    database, identity, identity_factory, workspace, mode
):
    from sqlalchemy.orm import Session

    from pmknowledge.auth import Principal
    from pmknowledge.retrieval import keyword_search, semantic_search

    class RankedEmbedder(FixtureEmbedder):
        def embed_passages(self, texts):
            return [
                vector(0.6, 0.8) if text == "Allowed service context." else vector(0.0, 1.0)
                for text in texts
            ]

    other = identity_factory()
    own, foreign = workspace(), workspace(headers=other.headers)
    app = create_app(
        Settings(
            database_url=database.url.render_as_string(hide_password=False), embeddings_enabled=True
        ),
        embedder=RankedEmbedder(),
    )
    with TestClient(app, headers=identity.headers) as api:
        allowed = upload(api, own, "Allowed service context.").json()
        for _ in range(21):
            response = api.post(
                f"/api/v1/workspaces/{foreign}/sources",
                data={"title": "Hidden synthetic metadata"},
                files={"file": ("a.txt", b"Service service service private-marker.")},
                headers=other.headers,
            )
            assert response.status_code == 201
        root = f"/api/v1/workspaces/{own}"
        hits = api.get(root + "/search", params={"q": "service", "mode": mode, "limit": 1}).json()[
            "results"
        ]
        assert [hit["source_document_id"] for hit in hits] == [allowed["source_document_id"]]
        answer = api.post(root + "/ask", json={"question": "service", "mode": mode}).json()
        assert [hit["chunk_id"] for hit in answer["sources"]] == [hits[0]["chunk_id"]]
        assert "private-marker" not in str(answer) and "Hidden synthetic" not in str(answer)
        assert (
            api.get(
                f"/api/v1/workspaces/{foreign}/search", params={"q": "service", "mode": mode}
            ).status_code
            == 404
        )
    # These lower-level queries must independently apply membership in SQL.
    with Session(database) as session:
        principal = Principal(identity.user_id)
        assert keyword_search(session, UUID(foreign), "service", 1, principal=principal) == []
        assert (
            semantic_search(
                session, UUID(foreign), "service", 1, RankedEmbedder(), 0.6, principal=principal
            )
            == []
        )


@pytest.mark.parametrize("mode", ["keyword", "semantic", "hybrid"])
def test_denied_workspace_never_invokes_inference(
    database, identity, identity_factory, workspace, mode
):
    class ForbiddenEmbedder(FixtureEmbedder):
        def embed_passages(self, texts):
            raise AssertionError("Denied upload reached inference")

        def embed_query(self, query):
            raise AssertionError("Denied query reached inference")

    foreign = workspace(headers=identity_factory().headers)
    app = create_app(
        Settings(
            database_url=database.url.render_as_string(hide_password=False), embeddings_enabled=True
        ),
        embedder=ForbiddenEmbedder(),
    )
    with TestClient(app, headers=identity.headers) as api:
        root = f"/api/v1/workspaces/{foreign}"
        assert api.get(root + "/search", params={"q": "evidence", "mode": mode}).status_code == 404
        assert (
            api.post(root + "/ask", json={"question": "evidence", "mode": mode}).status_code == 404
        )
        assert upload(api, foreign, "Synthetic evidence").status_code == 404
