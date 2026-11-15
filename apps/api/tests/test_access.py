"""Real credentials and SQL exercise the workspace authorization boundary."""

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from time import monotonic, sleep
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from test_api import upload

pytestmark = pytest.mark.integration


def test_operator_cli_token_lifecycle_and_explicit_legacy_ownership(database, client):
    def command(*arguments):
        result = subprocess.run(
            [sys.executable, "-m", "pmknowledge.auth", *arguments],
            env={**os.environ, "DATABASE_URL": database.url.render_as_string(hide_password=False)},
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    user = command("create-user", "--name", "Synthetic CLI operator")
    workspace_id = uuid4()
    try:
        with database.begin() as connection:
            connection.execute(
                text("INSERT INTO workspace (id, name) VALUES (:id, 'Legacy synthetic')"),
                {"id": workspace_id},
            )
        issued = command("issue-token", "--user-id", user["id"])
        headers = {"Authorization": f"Bearer {issued['token']}"}
        assert client.get("/api/v1/me", headers=headers).json()["id"] == user["id"]
        url = f"/api/v1/workspaces/{workspace_id}/search"
        assert client.get(url, params={"q": "evidence"}, headers=headers).status_code == 404
        for _ in range(2):
            command("grant-owner", "--workspace-id", str(workspace_id), "--user-id", user["id"])
        assert client.get(url, params={"q": "evidence"}, headers=headers).status_code == 200
        command("revoke-token", "--token-id", issued["id"])
        command("revoke-token", "--token-id", issued["id"])
        assert client.get("/api/v1/me", headers=headers).status_code == 401
    finally:
        with database.begin() as connection:
            connection.execute(text("DELETE FROM workspace WHERE id=:id"), {"id": workspace_id})
            connection.execute(text("DELETE FROM app_user WHERE id=:id"), {"id": UUID(user["id"])})


def test_identity_and_workspace_discovery_are_scoped(client, identity, identity_factory, workspace):
    own = workspace()
    outsider = identity_factory()
    assert client.get("/api/v1/me").json()["id"] == str(identity.user_id)
    listed = client.get("/api/v1/workspaces").json()["workspaces"]
    assert [(w["id"], w["role"]) for w in listed] == [(own, "owner")]
    assert client.get("/api/v1/workspaces", headers=outsider.headers).json() == {"workspaces": []}


@pytest.mark.parametrize("role,write_status", [("reader", 403), ("editor", 201), ("owner", 201)])
def test_roles_enforce_reads_writes_and_membership_management(
    client, identity_factory, workspace, role, write_status
):
    workspace_id = workspace()
    source = upload(client, workspace_id).json()["source_document_id"]
    member = identity_factory()
    root = f"/api/v1/workspaces/{workspace_id}"
    members = f"{root}/members"
    assert client.put(f"{members}/{member.user_id}", json={"role": role}).status_code == 200
    assert (
        client.get(
            f"{root}/search", params={"q": "troubleshooting"}, headers=member.headers
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"{root}/ask", json={"question": "troubleshooting"}, headers=member.headers
        ).json()["status"]
        == "grounded"
    )
    for suffix, data in [("/sources", {"title": "Synthetic"}), (f"/sources/{source}/versions", {})]:
        assert (
            client.post(
                root + suffix,
                data=data,
                files={"file": ("synthetic.txt", b"New evidence")},
                headers=member.headers,
            ).status_code
            == write_status
        )
    expected = 200 if role == "owner" else 403
    assert client.get(members, headers=member.headers).status_code == expected
    assert client.put(
        f"{members}/{uuid4()}", json={"role": "reader"}, headers=member.headers
    ).status_code == (404 if role == "owner" else 403)
    assert client.delete(f"{members}/{uuid4()}", headers=member.headers).status_code == (
        404 if role == "owner" else 403
    )


def test_nonmembers_cannot_probe_workspaces_or_spoof_identity(
    client, identity, identity_factory, workspace
):
    root = f"/api/v1/workspaces/{workspace()}"
    outsider = identity_factory()
    headers = {**outsider.headers, "X-User-ID": str(identity.user_id), "X-Role": "owner"}
    for suffix in ["/search?q=evidence", "/members"]:
        existing = client.get(root + suffix, headers=headers)
        missing = client.get(f"/api/v1/workspaces/{uuid4()}" + suffix, headers=headers)
        assert existing.status_code == missing.status_code == 404
        assert existing.json() == missing.json()
    assert (
        client.post(root + "/ask", json={"question": "evidence"}, headers=headers).status_code
        == 404
    )
    assert (
        client.post(
            root + "/sources",
            data={"title": "Synthetic"},
            files={"file": ("a.txt", b"evidence")},
            headers=headers,
        ).status_code
        == 404
    )
    assert (
        client.put(
            root + f"/members/{outsider.user_id}", json={"role": "owner"}, headers=headers
        ).status_code
        == 404
    )


def test_membership_revocation_and_demotion_apply_on_next_request(
    client, identity_factory, workspace
):
    root = f"/api/v1/workspaces/{workspace()}"
    member = identity_factory()
    member_url = root + f"/members/{member.user_id}"
    assert client.put(member_url, json={"role": "editor"}).status_code == 200
    assert (
        client.post(
            root + "/sources",
            data={"title": "Synthetic"},
            files={"file": ("a.txt", b"evidence")},
            headers=member.headers,
        ).status_code
        == 201
    )
    assert client.put(member_url, json={"role": "reader"}).status_code == 200
    assert (
        client.post(
            root + "/sources",
            data={"title": "Synthetic"},
            files={"file": ("a.txt", b"changed")},
            headers=member.headers,
        ).status_code
        == 403
    )
    assert (
        client.get(root + "/search", params={"q": "evidence"}, headers=member.headers).status_code
        == 200
    )
    assert client.delete(member_url).status_code == 204
    assert (
        client.get(root + "/search", params={"q": "evidence"}, headers=member.headers).status_code
        == 404
    )


def test_last_owner_cannot_be_removed_or_demoted_but_can_transfer(
    client, identity, identity_factory, workspace
):
    root = f"/api/v1/workspaces/{workspace()}/members"
    own = root + f"/{identity.user_id}"
    assert client.delete(own).status_code == 409
    assert client.put(own, json={"role": "reader"}).status_code == 409
    other = identity_factory()
    assert client.put(root + f"/{other.user_id}", json={"role": "owner"}).status_code == 200
    assert client.put(own, json={"role": "reader"}).status_code == 200
    assert client.get(root).status_code == 403
    assert client.get(root, headers=other.headers).status_code == 200


def test_expired_unknown_and_revoked_tokens_share_safe_response(client, identity, database, caplog):
    assert client.get("/api/v1/me").status_code == 200
    with database.begin() as connection:
        connection.execute(
            text("UPDATE api_token SET expires_at=:past WHERE id=:id"),
            {"past": datetime.now(UTC) - timedelta(seconds=1), "id": identity.token_id},
        )
    expired = client.get("/api/v1/me")
    unknown = client.get("/api/v1/me", headers={"Authorization": "Bearer " + "x" * 43})
    assert expired.status_code == unknown.status_code == 401
    assert expired.json() == unknown.json() == {"detail": "Invalid or missing credentials"}
    assert expired.headers["www-authenticate"] == "Bearer"
    assert identity.token not in caplog.text + expired.text
    with database.connect() as connection:
        row = connection.execute(
            text("SELECT token_hash FROM api_token WHERE id=:id"), {"id": identity.token_id}
        ).scalar_one()
        assert len(row) == 64 and identity.token not in row


def test_concurrent_owner_demotions_retain_one_owner(client, identity, identity_factory, workspace):
    root = f"/api/v1/workspaces/{workspace()}/members"
    other = identity_factory()
    assert client.put(root + f"/{other.user_id}", json={"role": "owner"}).status_code == 200
    barrier = Barrier(2)

    def demote(actor):
        barrier.wait(timeout=5)
        return client.put(
            root + f"/{actor.user_id}", json={"role": "reader"}, headers=actor.headers
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(demote, [identity, other]))
    assert sorted(r.status_code for r in responses) == [200, 409]
    owner = other if responses[0].status_code == 200 else identity
    members = client.get(root, headers=owner.headers).json()["members"]
    assert sum(m["role"] == "owner" for m in members) == 1


def test_waiting_owner_is_rechecked_after_lock(client, database, identity_factory, workspace):
    workspace_id = workspace()
    root = f"/api/v1/workspaces/{workspace_id}/members"
    actor, target = identity_factory(), identity_factory()
    assert client.put(root + f"/{actor.user_id}", json={"role": "owner"}).status_code == 200
    with ThreadPoolExecutor(max_workers=1) as pool, database.connect() as lock:
        transaction = lock.begin()
        try:
            lock.execute(
                text("SELECT id FROM workspace WHERE id=:id FOR UPDATE"), {"id": UUID(workspace_id)}
            )
            waiting = pool.submit(
                client.put,
                root + f"/{target.user_id}",
                json={"role": "owner"},
                headers=actor.headers,
            )
            deadline = monotonic() + 5
            blocked = False
            while monotonic() < deadline:
                with database.connect() as observer:
                    blocked = observer.scalar(
                        text(
                            "SELECT EXISTS (SELECT 1 FROM pg_stat_activity "
                            "WHERE datname=current_database() AND wait_event_type='Lock' "
                            "AND query LIKE '%FOR UPDATE%')"
                        )
                    )
                if blocked:
                    break
                sleep(0.01)
            assert blocked, "Membership writer did not acquire the workspace serialization lock"
            lock.execute(
                text(
                    "UPDATE workspace_membership SET role='editor' "
                    "WHERE workspace_id=:workspace AND user_id=:user"
                ),
                {"workspace": UUID(workspace_id), "user": actor.user_id},
            )
            transaction.commit()
        finally:
            if transaction.is_active:
                transaction.rollback()
        assert waiting.result(timeout=10).status_code == 403
    assert str(target.user_id) not in {m["user_id"] for m in client.get(root).json()["members"]}


@pytest.mark.parametrize("days", [0, -1, 10**20])
def test_invalid_token_lifetime_leaves_no_credentials(database, identity, days):
    from fastapi import HTTPException
    from sqlalchemy.orm import Session

    from pmknowledge.auth import issue_token

    with Session(database) as session, session.begin():
        with pytest.raises((ValueError, HTTPException)):
            issue_token(session, identity.user_id, days)
    with database.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT count(*) FROM api_token WHERE user_id=:id"), {"id": identity.user_id}
            )
            == 1
        )


def test_revocation_does_not_revoke_other_tokens_for_the_user(database, client, identity):
    from sqlalchemy.orm import Session

    from pmknowledge.auth import issue_token, revoke_token

    with Session(database) as session, session.begin():
        record, another = issue_token(session, identity.user_id, 1)
        assert timedelta(hours=23) < record.expires_at - datetime.now(UTC) <= timedelta(days=1)
        revoke_token(session, identity.token_id)
    assert client.get("/api/v1/me").status_code == 401
    assert (
        client.get("/api/v1/me", headers={"Authorization": f"Bearer {another}"}).status_code == 200
    )
