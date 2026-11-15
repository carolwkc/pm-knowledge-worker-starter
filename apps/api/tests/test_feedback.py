"""Feedback is scoped user opinion, never a trusted query log or decision."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from test_api import upload

pytestmark = pytest.mark.integration


def path(wid):
    return f"/api/v1/workspaces/{wid}/feedback"


def payload(client, wid, *, empty=False):
    if not empty:
        upload(client, wid, "Synthetic café quartz evidence.\r\n".encode())
    question = "nonexistentplatypus" if empty else "quartz"
    answer = client.post(f"/api/v1/workspaces/{wid}/ask", json={"question": question}).json()
    return {
        "submission_id": str(uuid4()),
        "question": question,
        "mode": "keyword",
        "answer": answer,
        "rating": "not_helpful",
        "reason": "missing_evidence",
        "comment": "  Synthetic feedback 👋  ",
    }


@pytest.mark.parametrize("role", ["reader", "editor", "owner"])
@pytest.mark.parametrize("empty", [False, True])
def test_members_submit_and_only_owners_inspect(client, workspace, identity_factory, role, empty):
    wid = workspace()
    body = payload(client, wid, empty=empty)
    member = identity_factory()
    client.put(f"/api/v1/workspaces/{wid}/members/{member.user_id}", json={"role": role})
    response = client.post(path(wid), json=body, headers=member.headers)
    assert response.status_code == 201
    receipt = response.json()
    assert receipt["workspace_id"] == wid
    assert receipt["submission_id"] == body["submission_id"]
    assert response.headers["cache-control"] == "no-store"
    detail = client.get(f"{path(wid)}/{receipt['id']}").json()
    assert detail["created_by"] == str(member.user_id)
    assert detail["answer"] == body["answer"]
    assert detail["comment"] == "Synthetic feedback 👋"
    assert detail["question"] == body["question"]
    for url in [path(wid), f"{path(wid)}/{receipt['id']}"]:
        assert client.get(url, headers=member.headers).status_code == (
            200 if role == "owner" else 403
        )


def test_retry_normalization_conflict_and_concurrency(client, workspace, database):
    wid = workspace()
    body = payload(client, wid)
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda _: client.post(path(wid), json=body), range(4)))
    assert sorted(r.status_code for r in responses) == [200, 200, 200, 201]
    assert all(r.json() == responses[0].json() for r in responses)
    body["comment"] = "Synthetic feedback 👋"
    assert client.post(path(wid), json=body).json() == responses[0].json()
    body["rating"] = "helpful"
    body["reason"] = None
    assert client.post(path(wid), json=body).status_code == 409
    with database.connect() as conn:
        assert (
            conn.scalar(
                text("SELECT count(*) FROM answer_feedback WHERE workspace_id=:wid"),
                {"wid": UUID(wid)},
            )
            == 1
        )


def test_history_and_foreign_or_fabricated_evidence(client, workspace, identity_factory):
    wid, foreign = workspace(), workspace()
    body = payload(client, wid)
    source = body["answer"]["sources"][0]
    upload(client, wid, b"New current evidence.", source_id=source["source_document_id"])
    assert client.post(path(wid), json=body).status_code == 201
    foreign_body = payload(client, foreign)
    member = identity_factory()
    client.put(f"/api/v1/workspaces/{wid}/members/{member.user_id}", json={"role": "reader"})
    foreign_body["submission_id"] = str(uuid4())
    assert client.post(path(wid), json=foreign_body, headers=member.headers).status_code == 404
    for field, value in [
        ("chunk_id", str(uuid4())),
        ("document_version_id", str(uuid4())),
        ("source_document_id", str(uuid4())),
    ]:
        changed = deepcopy(body)
        changed["submission_id"] = str(uuid4())
        changed["answer"]["sources"][0][field] = value
        assert client.post(path(wid), json=changed).status_code == 404
    for field, value in [
        ("excerpt", "Fabricated quotation"),
        ("start_char", 1),
        ("title", "Forged title"),
        ("citation", "99"),
    ]:
        changed = deepcopy(body)
        changed["submission_id"] = str(uuid4())
        changed["answer"]["sources"][0][field] = value
        assert client.post(path(wid), json=changed).status_code == 422
    body["submission_id"] = str(uuid4())
    body["answer"]["answer"] = "Fabricated answer"
    assert client.post(path(wid), json=body).status_code == 422


@pytest.mark.parametrize(
    "change",
    [
        {"question": "x" * 1001},
        {"question": "bad\0question"},
        {"comment": "👋" * 1001},
        {"comment": "bad\0comment"},
        {"rating": "helpful"},
        {"reason": "invalid"},
        {"created_by": str(uuid4())},
        {"mode": "invalid"},
        {"question": "   "},
    ],
)
def test_safe_validation(client, workspace, change):
    wid = workspace()
    body = payload(client, wid, empty=True)
    body.update(change)
    response = client.post(path(wid), json=body)
    assert response.status_code == 422
    assert all("input" not in error for error in response.json()["detail"])
    assert response.headers["cache-control"] == "no-store"


def test_pagination_scope_revocation_and_retention(client, workspace, identity_factory, database):
    wid, other = workspace(), workspace()
    body = payload(client, wid, empty=True)
    ids = []
    for i in range(3):
        body.update(
            submission_id=str(uuid4()),
            rating="helpful" if i == 0 else "not_helpful",
            reason=None,
            comment=" " if i == 0 else "👋" * 1000,
        )
        response = client.post(path(wid), json=body)
        assert response.status_code == 201
        ids.append(response.json()["id"])
    first = client.get(path(wid), params={"limit": 2}).json()
    assert [r["id"] for r in first["feedback"]] == list(reversed(ids))[:2]
    assert first["has_more"] is True
    assert "answer" not in first["feedback"][0]
    assert client.get(path(wid), params={"limit": 2, "offset": 2}).json()["has_more"] is False
    helpful = client.get(path(wid), params={"rating": "helpful"}).json()["feedback"]
    assert [r["id"] for r in helpful] == ids[:1]
    assert client.get(f"{path(wid)}/{ids[0]}").json()["comment"] is None
    assert client.get(f"{path(other)}/{ids[0]}").status_code == 404
    member = identity_factory()
    assert client.post(path(wid), json=body, headers=member.headers).status_code == 404
    assert client.get(path(wid), headers=member.headers).status_code == 404
    for params in [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"rating": "invalid"}]:
        assert client.get(path(wid), params=params).status_code == 422
    client.headers.pop("Authorization")
    assert client.get(path(wid)).status_code == 401
    with database.begin() as conn:
        conn.execute(text("DELETE FROM workspace WHERE id=:wid"), {"wid": UUID(wid)})
        assert (
            conn.scalar(
                text("SELECT count(*) FROM answer_feedback WHERE workspace_id=:wid"),
                {"wid": UUID(wid)},
            )
            == 0
        )


def test_snapshot_bounds_auth_and_ordinary_questions_are_not_saved(
    client, workspace, database, identity_factory
):
    wid = workspace()
    body = payload(client, wid)
    with database.connect() as conn:
        assert (
            conn.scalar(
                text("SELECT count(*) FROM answer_feedback WHERE workspace_id=:wid"),
                {"wid": UUID(wid)},
            )
            == 0
        )
    for answer in [
        {**body["answer"], "answer": "x" * 4097},
        {**body["answer"], "sources": body["answer"]["sources"] * 4},
        {**body["answer"], "unexpected": "sensitive"},
        {**body["answer"], "status": "insufficient_evidence"},
    ]:
        response = client.post(path(wid), json={**body, "answer": answer})
        assert response.status_code == 422
    member = identity_factory()
    member_url = f"/api/v1/workspaces/{wid}/members/{member.user_id}"
    client.put(member_url, json={"role": "owner"})
    receipt = client.post(path(wid), json=body, headers=member.headers).json()
    client.put(member_url, json={"role": "reader"})
    assert client.get(f"{path(wid)}/{receipt['id']}", headers=member.headers).status_code == 403
    client.delete(member_url)
    assert client.post(path(wid), json=body, headers=member.headers).status_code == 404
    with database.begin() as conn:
        conn.execute(
            text("UPDATE api_token SET revoked_at=now() WHERE id=:id"), {"id": member.token_id}
        )
    assert client.post(path(wid), json=body, headers=member.headers).status_code == 401


def test_concurrent_conflicting_submissions_and_retention_after_source_removal(
    client, workspace, database
):
    wid = workspace()
    first = payload(client, wid)
    second = {**first, "comment": "A different synthetic opinion"}
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda body: client.post(path(wid), json=body), [first, second]))
    assert sorted(response.status_code for response in responses) == [201, 409]
    winner = next(i for i, response in enumerate(responses) if response.status_code == 201)
    body = [first, second][winner]
    receipt = responses[winner].json()
    source_id = body["answer"]["sources"][0]["source_document_id"]
    with database.begin() as conn:
        conn.execute(text("DELETE FROM source_document WHERE id=:id"), {"id": UUID(source_id)})
    detail = client.get(f"{path(wid)}/{receipt['id']}")
    assert detail.status_code == 200
    assert detail.json()["answer"] == body["answer"]
    replay = client.post(path(wid), json=body)
    assert replay.status_code == 200
    assert replay.json() == receipt
    evidence = body["answer"]["sources"][0]
    assert (
        client.get(
            f"/api/v1/workspaces/{wid}/sources/{source_id}/versions/{evidence['document_version_id']}"
        ).status_code
        == 404
    )
