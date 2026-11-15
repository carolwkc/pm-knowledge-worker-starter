"""Source context stays pinned to immutable evidence and current workspace access."""

import hashlib
from uuid import uuid4

import pytest
from sqlalchemy import text
from test_api import upload

pytestmark = pytest.mark.integration


def version_url(workspace_id, receipt):
    return (
        f"/api/v1/workspaces/{workspace_id}/sources/{receipt['source_document_id']}"
        f"/versions/{receipt['document_version_id']}"
    )


@pytest.mark.parametrize("role", ["reader", "editor", "owner"])
def test_member_reads_exact_source_and_historical_citation(
    client, workspace, identity_factory, role
):
    workspace_id = workspace()
    content = "# Synthetic café 👋\r\n\r\nTroubleshooting acceleration.\r\n"
    receipt = upload(
        client,
        workspace_id,
        content.encode(),
        title="Synthetic café",
        external_uri="javascript:inert",
    ).json()
    member = identity_factory()
    client.put(f"/api/v1/workspaces/{workspace_id}/members/{member.user_id}", json={"role": role})
    url = version_url(workspace_id, receipt)
    response = client.get(url, headers=member.headers)
    assert response.status_code == 200
    result = response.json()
    assert result == {
        "workspace_id": workspace_id,
        "source_document_id": receipt["source_document_id"],
        "document_version_id": receipt["document_version_id"],
        "title": "Synthetic café",
        "external_uri": "javascript:inert",
        "version_number": 1,
        "sha256": hashlib.sha256(content.encode()).hexdigest(),
        "ingested_at": result["ingested_at"],
        "plain_text": content,
        "source_is_latest": True,
    }
    assert result["ingested_at"]
    answer = client.post(
        f"/api/v1/workspaces/{workspace_id}/ask", json={"question": "troubleshooting"}
    ).json()
    citation = answer["sources"][0]
    assert (
        result["plain_text"][citation["start_char"] : citation["end_char"]] == citation["excerpt"]
    )
    updated = upload(
        client,
        workspace_id,
        b"Changed synthetic evidence.",
        source_id=receipt["source_document_id"],
    ).json()
    historical = client.get(url, headers=member.headers).json()
    assert historical == {**result, "source_is_latest": False}
    assert client.get(version_url(workspace_id, updated)).json()["source_is_latest"] is True


def test_source_lookup_scopes_workspace_source_and_version(client, workspace, identity_factory):
    first, second = workspace(), workspace()
    a, b = upload(client, first).json(), upload(client, second).json()
    outsider = identity_factory()
    assert client.get(version_url(first, a), headers=outsider.headers).status_code == 404
    paths = [
        version_url(second, a),
        version_url(first, {**a, "document_version_id": b["document_version_id"]}),
        version_url(first, {**a, "source_document_id": b["source_document_id"]}),
        version_url(first, {**a, "source_document_id": str(uuid4())}),
        version_url(first, {**a, "document_version_id": str(uuid4())}),
    ]
    for path in paths:
        response = client.get(path)
        assert response.status_code == 404
        assert "plain_text" not in response.text
    assert client.get(version_url(str(uuid4()), a)).status_code == 404
    client.put(f"/api/v1/workspaces/{first}/members/{outsider.user_id}", json={"role": "reader"})
    assert client.get(version_url(first, a), headers=outsider.headers).status_code == 200
    client.delete(f"/api/v1/workspaces/{first}/members/{outsider.user_id}")
    assert client.get(version_url(first, a), headers=outsider.headers).status_code == 404


def test_api_responses_never_cached_including_auth_validation_and_errors(
    client, workspace, identity, database, caplog
):
    receipt = upload(client, workspace()).json()
    url = version_url(receipt["workspace_id"], receipt)
    for path in [url, "/api/v1/me", "/api/v1/workspaces", "/api/v1/missing", url + "invalid"]:
        assert client.get(path).headers.get("cache-control") == "no-store"
    client.headers.pop("Authorization")
    missing = client.get(url)
    assert missing.status_code == 401
    assert missing.headers["www-authenticate"] == "Bearer"
    assert missing.headers.get("cache-control") == "no-store"
    with database.begin() as connection:
        connection.execute(
            text("UPDATE api_token SET revoked_at=now() WHERE id=:id"), {"id": identity.token_id}
        )
    revoked = client.get(url, headers=identity.headers)
    assert revoked.status_code == 401
    assert revoked.headers.get("cache-control") == "no-store"
    assert identity.token not in caplog.text
