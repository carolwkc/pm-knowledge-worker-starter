"""Use actual PostgreSQL lock waits and transactions, not timing guesses."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from time import monotonic, sleep
from uuid import UUID

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import SQLAlchemyError
from test_decisions import proposals, review, source

pytestmark = pytest.mark.integration


def wait_for_lock(database, table):
    deadline = monotonic() + 5
    while monotonic() < deadline:
        with database.connect() as observer:
            if observer.scalar(
                text(
                    "SELECT EXISTS (SELECT 1 FROM pg_stat_activity "
                    "WHERE datname=current_database() AND wait_event_type='Lock' "
                    "AND query LIKE :pattern "
                    "AND (query LIKE '%FOR UPDATE%' OR query LIKE '%FOR KEY SHARE%'))"
                ),
                {"pattern": f"%{table}%"},
            ):
                return
        sleep(0.01)
    pytest.fail(f"Request did not wait for the {table} lock")


def test_concurrent_generation_reuses_proposals_and_original_proposer(
    client, workspace, identity_factory
):
    root, _, generate = source(client, workspace())
    editor = identity_factory()
    client.put(root + f"/members/{editor.user_id}", json={"role": "editor"})
    barrier = Barrier(2)

    def generate_once(headers):
        barrier.wait(timeout=5)
        return proposals(client, generate, headers=headers)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(generate_once, [{}, editor.headers]))
    assert sorted(r["created_count"] for r in results) == [0, 1]
    assert results[0]["proposals"] == results[1]["proposals"]
    assert client.get(root + "/proposals?status=all").json()["proposals"] == results[0]["proposals"]


@pytest.mark.parametrize("actions", [("approve", "reject"), ("approve", "approve")])
def test_concurrent_reviews_have_one_terminal_event(client, workspace, database, actions):
    root, _, generate = source(client, workspace())
    p = proposals(client, generate)["proposals"][0]
    barrier = Barrier(2)

    def run(action):
        barrier.wait(timeout=5)
        return review(client, root, p, action)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, actions))
    assert sorted(r.status_code for r in results) == (
        [200, 200] if actions[0] == actions[1] else [200, 409]
    )
    stored = client.get(root + f"/proposals/{p['id']}").json()
    with database.connect() as conn:
        assert (
            conn.scalar(
                text("SELECT count(*) FROM review_event WHERE proposal_id=:id"),
                {"id": UUID(p["id"])},
            )
            == 1
        )
    decisions = client.get(root + "/decisions").json()["decisions"]
    assert len(decisions) == (1 if stored["status"] == "approved" else 0)
    if actions[0] == actions[1]:
        assert results[0].json() == results[1].json()


def test_approval_rechecks_latest_after_waiting_for_source_lock(client, workspace, database):
    root, receipt, generate = source(client, workspace())
    p = proposals(client, generate)["proposals"][0]
    with database.connect() as lock, ThreadPoolExecutor(max_workers=2) as pool:
        transaction = lock.begin()
        try:
            lock.execute(
                text("SELECT id FROM source_document WHERE id=:id FOR UPDATE"),
                {"id": UUID(receipt["source_document_id"])},
            )
            # A normal upload takes the same source lock. Observe it waiting first.
            upload = pool.submit(
                client.post,
                root + f"/sources/{receipt['source_document_id']}/versions",
                files={"file": ("new.txt", b"Decision: use a newer source.")},
            )
            wait_for_lock(database, "source_document")
            pending = pool.submit(review, client, root, p)
            # Wait until BOTH the uploader and reviewer have reached the lock.
            deadline = monotonic() + 5
            while monotonic() < deadline:
                with database.connect() as observer:
                    count = observer.scalar(
                        text(
                            "SELECT count(*) FROM pg_stat_activity "
                            "WHERE datname=current_database() "
                            "AND wait_event_type='Lock' AND query LIKE '%source_document%' "
                            "AND query LIKE '%FOR UPDATE%'"
                        )
                    )
                if count == 2:
                    break
                sleep(0.01)
            assert count == 2
            transaction.commit()
        finally:
            if transaction.is_active:
                transaction.rollback()
        assert upload.result(timeout=10).status_code == 201
        assert pending.result(timeout=10).status_code == 409
    assert client.get(root + f"/proposals/{p['id']}").json()["status"] == "pending"
    assert client.get(root + "/decisions").json() == {"decisions": []}


def test_waiting_reviewer_is_rechecked_after_owner_demotion(
    client, workspace, database, identity_factory
):
    workspace_id = workspace()
    root, _, generate = source(client, workspace_id)
    p = proposals(client, generate)["proposals"][0]
    actor = identity_factory()
    client.put(root + f"/members/{actor.user_id}", json={"role": "owner"})
    with database.connect() as lock, ThreadPoolExecutor(max_workers=1) as pool:
        transaction = lock.begin()
        try:
            lock.execute(
                text("SELECT id FROM workspace WHERE id=:id FOR UPDATE"), {"id": UUID(workspace_id)}
            )
            pending = pool.submit(review, client, root, p, headers=actor.headers)
            wait_for_lock(database, "workspace")
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
        assert pending.result(timeout=10).status_code == 403
    assert client.get(root + "/decisions").json() == {"decisions": []}
    assert client.get(root + f"/proposals/{p['id']}").json()["review"] is None


def test_waiting_extractor_is_rechecked_after_editor_demotion(
    client, workspace, database, identity_factory
):
    workspace_id = workspace()
    root, _, generate = source(client, workspace_id)
    actor = identity_factory()
    client.put(root + f"/members/{actor.user_id}", json={"role": "editor"})
    with database.connect() as lock, ThreadPoolExecutor(max_workers=1) as pool:
        transaction = lock.begin()
        try:
            lock.execute(
                text("SELECT id FROM workspace WHERE id=:id FOR UPDATE"),
                {"id": UUID(workspace_id)},
            )
            pending = pool.submit(client.post, generate, headers=actor.headers)
            wait_for_lock(database, "workspace")
            lock.execute(
                text(
                    "UPDATE workspace_membership SET role='reader' "
                    "WHERE workspace_id=:workspace AND user_id=:user"
                ),
                {"workspace": UUID(workspace_id), "user": actor.user_id},
            )
            transaction.commit()
        finally:
            if transaction.is_active:
                transaction.rollback()
        assert pending.result(timeout=10).status_code == 403
    assert client.get(root + "/proposals?status=all").json() == {"proposals": []}


def test_failed_review_rolls_back_publication_and_status(client, workspace, database):
    from pmknowledge.models import ReviewEvent

    root, _, generate = source(client, workspace())
    p = proposals(client, generate)["proposals"][0]

    def fail_review_storage(*args):
        raise SQLAlchemyError("Synthetic storage failure")

    event.listen(ReviewEvent, "before_insert", fail_review_storage)
    try:
        assert review(client, root, p).status_code == 503
    finally:
        event.remove(ReviewEvent, "before_insert", fail_review_storage)
    stored = client.get(root + f"/proposals/{p['id']}").json()
    assert stored["status"] == "pending"
    assert stored["review"] is None and stored["decision_id"] is None
    assert client.get(root + "/decisions").json() == {"decisions": []}
    assert review(client, root, p).status_code == 200


def test_new_extraction_and_old_proposal_review_do_not_deadlock(client, workspace, database):
    from pmknowledge.models import KnowledgeProposal

    root, receipt, generate = source(client, workspace())
    old = proposals(client, generate)["proposals"][0]
    new = client.post(
        root + f"/sources/{receipt['source_document_id']}/versions",
        files={"file": ("new.txt", b"Decision: extract the new version.")},
    ).json()
    generate = generate.replace(receipt["document_version_id"], new["document_version_id"])
    ready, resume = Event(), Event()

    def pause_before_insert(*args):
        ready.set()
        assert resume.wait(timeout=10)

    event.listen(KnowledgeProposal, "before_insert", pause_before_insert)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            extraction = pool.submit(client.post, generate)
            try:
                assert ready.wait(timeout=5)
                reviewing = pool.submit(review, client, root, old)
                # Before the fix review waits on source; after it waits on workspace.
                wait_for_lock(database, "")
            finally:
                resume.set()
            extracted = extraction.result(timeout=15)
            reviewed = reviewing.result(timeout=15)
            assert extracted.status_code == 200, extracted.text
            assert reviewed.status_code == 409, reviewed.text
    finally:
        resume.set()
        event.remove(KnowledgeProposal, "before_insert", pause_before_insert)
    assert client.get(root + "/decisions").json() == {"decisions": []}
    assert len(client.get(root + "/proposals?status=all").json()["proposals"]) == 2


@pytest.mark.parametrize("listing", [False, True])
def test_proposal_read_uses_one_consistent_review_snapshot(client, workspace, listing):
    from sqlalchemy.engine import Engine

    root, _, generate = source(client, workspace())
    p = proposals(client, generate)["proposals"][0]
    ready, resume = Event(), Event()

    def pause_after_proposal_select(connection, cursor, statement, parameters, context, many):
        if statement.startswith("SELECT knowledge_proposal.id") and not ready.is_set():
            ready.set()
            assert resume.wait(timeout=10)

    event.listen(Engine, "after_cursor_execute", pause_after_proposal_select)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            reading = pool.submit(
                client.get, root + ("/proposals" if listing else f"/proposals/{p['id']}")
            )
            try:
                assert ready.wait(timeout=5)
                assert review(client, root, p).status_code == 200
            finally:
                resume.set()
            response = reading.result(timeout=10)
    finally:
        resume.set()
        event.remove(Engine, "after_cursor_execute", pause_after_proposal_select)
    assert response.status_code == 200
    snapshot = response.json()["proposals"][0] if listing else response.json()
    # Reading just before approval may return pending, but never a mixed state.
    assert snapshot["status"] == "pending"
    assert snapshot["review"] is None
    assert snapshot["decision_id"] is None
