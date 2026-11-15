"""Trusted test-only provisioning. Requires an explicitly selected *_test database."""

import json
import os
import sys
from uuid import UUID

from sqlalchemy import create_engine, delete
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from pmknowledge.auth import create_user, issue_token, revoke_token
from pmknowledge.models import User, Workspace, WorkspaceMembership

PREFIX = "Synthetic Task005 browser"


def main() -> None:
    url = os.environ.get("E2E_DATABASE_URL", "")
    parsed = make_url(url)
    if parsed.get_backend_name() != "postgresql" or not (parsed.database or "").endswith("_test"):
        raise ValueError("E2E_DATABASE_URL must explicitly select a PostgreSQL *_test database")
    engine = create_engine(url, hide_parameters=True)
    payload = json.load(sys.stdin)
    with Session(engine) as session, session.begin():
        if payload["action"] == "create":
            owner = create_user(session, PREFIX + " owner")
            reader = create_user(session, PREFIX + " reader")
            _, owner_token = issue_token(session, owner.id)
            reader_record, reader_token = issue_token(session, reader.id)
            aurora = Workspace(name=PREFIX + " Aurora")
            orbit = Workspace(name=PREFIX + " Orbit")
            session.add_all([aurora, orbit])
            session.flush()
            session.add_all(
                [
                    WorkspaceMembership(workspace_id=aurora.id, user_id=owner.id, role="owner"),
                    WorkspaceMembership(workspace_id=orbit.id, user_id=owner.id, role="owner"),
                    WorkspaceMembership(workspace_id=aurora.id, user_id=reader.id, role="reader"),
                ]
            )
            result = {
                "ownerToken": owner_token,
                "readerToken": reader_token,
                "readerTokenId": str(reader_record.id),
                "workspaces": [str(aurora.id), str(orbit.id)],
                "users": [str(owner.id), str(reader.id)],
            }
        elif payload["action"] == "revoke":
            revoke_token(session, UUID(payload["tokenId"]))
            result = {}
        elif payload["action"] == "cleanup":
            session.execute(
                delete(Workspace).where(
                    Workspace.id.in_([UUID(value) for value in payload["workspaces"]]),
                    Workspace.name.startswith(PREFIX),
                )
            )
            session.execute(
                delete(User).where(
                    User.id.in_([UUID(value) for value in payload["users"]]),
                    User.name.startswith(PREFIX),
                )
            )
            result = {}
        else:
            raise ValueError("Unknown test fixture action")
    engine.dispose()
    print(json.dumps(result))


if __name__ == "__main__":
    main()
