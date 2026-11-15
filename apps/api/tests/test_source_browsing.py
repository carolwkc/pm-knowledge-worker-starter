"""Browse metadata without leaking foreign sources or changing immutable evidence."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from test_api import upload

pytestmark = pytest.mark.integration


def catalogue(workspace_id):
    return f"/api/v1/workspaces/{workspace_id}/sources"


@pytest.mark.parametrize("role", ["reader", "editor", "owner"])
def test_members_browse_latest_metadata_and_immutable_history(
    client, workspace, identity_factory, role
):
    wid = workspace()
    first = upload(client, wid, b"Original synthetic evidence.", title="Synthetic guide").json()
    second = upload(
        client, wid, b"Updated synthetic evidence.", source_id=first["source_document_id"]
    ).json()
    # Re-uploading old content must not reactivate the old version.
    upload(client, wid, b"Original synthetic evidence.", source_id=first["source_document_id"])
    member = identity_factory()
    client.put(f"/api/v1/workspaces/{wid}/members/{member.user_id}", json={"role": role})
    response = client.get(catalogue(wid), headers=member.headers)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    result = response.json()
    assert result["has_more"] is False
    source = result["sources"][0]
    assert source == {
        "workspace_id": wid,
        "source_document_id": first["source_document_id"],
        "title": "Synthetic guide",
        "external_uri": None,
        "created_at": source["created_at"],
        "latest_version_id": second["document_version_id"],
        "latest_version_number": 2,
        "latest_ingested_at": source["latest_ingested_at"],
    }
    history_url = f"{catalogue(wid)}/{first['source_document_id']}/versions"
    history = client.get(history_url, headers=member.headers)
    assert history.status_code == 200
    assert history.headers["cache-control"] == "no-store"
    versions = history.json()["versions"]
    assert [v["document_version_id"] for v in versions] == [
        second["document_version_id"],
        first["document_version_id"],
    ]
    assert [v["source_is_latest"] for v in versions] == [True, False]
    for version in versions:
        assert set(version) == {
            "workspace_id",
            "source_document_id",
            "document_version_id",
            "version_number",
            "sha256",
            "ingested_at",
            "source_is_latest",
        }
        assert version["workspace_id"] == wid
        assert version["source_document_id"] == first["source_document_id"]
    old = client.get(f"{history_url}/{first['document_version_id']}", headers=member.headers)
    assert old.json()["plain_text"] == "Original synthetic evidence."


def test_browse_filters_and_pages_inside_workspace(client, workspace, database):
    wid, other = workspace(), workspace()
    receipts = [
        upload(client, wid, title=title).json()
        for title in ["Roadmap 100%_ready", "Roadmap normal", "Other / notes"]
    ]
    upload(client, other, title="Foreign Roadmap")
    # Force timestamp ties to exercise the UUID tiebreaker.
    with database.begin() as connection:
        connection.execute(
            text("UPDATE source_document SET created_at='2026-01-01' WHERE workspace_id=:wid"),
            {"wid": UUID(wid)},
        )
    url = catalogue(wid)
    expected = sorted(r["source_document_id"] for r in receipts)
    first = client.get(url, params={"limit": 2}).json()
    assert [s["source_document_id"] for s in first["sources"]] == expected[:2]
    assert first["has_more"] is True
    last = client.get(url, params={"limit": 2, "offset": 2}).json()
    assert [s["source_document_id"] for s in last["sources"]] == expected[2:]
    assert last["has_more"] is False
    for title, wanted in [("  ROADMAP  ", 2), ("%_", 1), ("/", 1), ("   ", 3), ("missing", 0)]:
        result = client.get(url, params={"title": title}).json()
        assert len(result["sources"]) == wanted
        assert result["has_more"] is False
    history_url = f"{url}/{receipts[0]['source_document_id']}/versions"
    for n in range(2, 4):
        upload(
            client,
            wid,
            f"Synthetic version {n}".encode(),
            source_id=receipts[0]["source_document_id"],
        )
    page = client.get(history_url, params={"limit": 2}).json()
    assert [v["version_number"] for v in page["versions"]] == [3, 2]
    assert page["has_more"] is True
    tail = client.get(history_url, params={"limit": 2, "offset": 2}).json()
    assert [v["version_number"] for v in tail["versions"]] == [1]
    assert tail["has_more"] is False
    assert client.get(url, params={"offset": 100}).json() == {"sources": [], "has_more": False}


def test_browse_access_and_empty_results(client, workspace, identity_factory, database):
    wid, foreign = workspace(), workspace()
    assert client.get(catalogue(wid)).json() == {"sources": [], "has_more": False}
    source = upload(client, foreign).json()["source_document_id"]
    member = identity_factory()
    client.put(f"/api/v1/workspaces/{wid}/members/{member.user_id}", json={"role": "reader"})
    paths = [catalogue(foreign), f"{catalogue(wid)}/{source}/versions", catalogue(uuid4())]
    for path in paths:
        response = client.get(path, headers=member.headers)
        assert response.status_code == 404
        assert response.headers["cache-control"] == "no-store"
    client.delete(f"/api/v1/workspaces/{wid}/members/{member.user_id}")
    assert client.get(catalogue(wid), headers=member.headers).status_code == 404
    with database.begin() as connection:
        connection.execute(
            text("UPDATE api_token SET revoked_at=now() WHERE id=:id"), {"id": member.token_id}
        )
    for path in [catalogue(wid), f"{catalogue(foreign)}/{source}/versions"]:
        response = client.get(path, headers=member.headers)
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"
    client.headers.pop("Authorization")
    assert client.get(catalogue(wid)).status_code == 401


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_browse_pagination_validation(client, workspace, params):
    wid = workspace()
    receipt = upload(client, wid).json()
    for url in [catalogue(wid), f"{catalogue(wid)}/{receipt['source_document_id']}/versions"]:
        response = client.get(url, params=params)
        assert response.status_code == 422
        assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("title", ["x" * 201, "bad\x00title"])
def test_browse_rejects_invalid_title(client, workspace, title):
    assert client.get(catalogue(workspace()), params={"title": title}).status_code == 422
