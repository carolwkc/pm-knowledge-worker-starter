"""Local opaque credentials and trusted database-operator provisioning commands."""

import argparse
import hashlib
import json
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from pmknowledge.config import Settings
from pmknowledge.models import ApiToken, User, Workspace, WorkspaceMembership
from pmknowledge.schemas import UserCreate, UserRead


@dataclass(frozen=True)
class Principal:
    user_id: UUID


def invalid_credentials() -> HTTPException:
    return HTTPException(
        401, "Invalid or missing credentials", headers={"WWW-Authenticate": "Bearer"}
    )


def authenticate(session: Session, token: str) -> Principal:
    # token_urlsafe(32) yields exactly 43 URL-safe characters, with 256 bits of entropy.
    if re.fullmatch(r"[A-Za-z0-9_-]{43}", token) is None:
        raise invalid_credentials()
    user_id = session.scalar(
        select(ApiToken.user_id).where(
            ApiToken.token_hash == hashlib.sha256(token.encode("ascii")).hexdigest(),
            ApiToken.revoked_at.is_(None),
            ApiToken.expires_at > func.now(),
        )
    )
    if user_id is None:
        raise invalid_credentials()
    return Principal(user_id=user_id)


def create_user(session: Session, name: str) -> User:
    user = User(name=UserCreate(name=name).name)
    session.add(user)
    session.flush()
    return user


def issue_token(session: Session, user_id: UUID, expires_in_days: int = 30) -> tuple[ApiToken, str]:
    if expires_in_days <= 0:
        raise ValueError("Token lifetime must be positive")
    if session.get(User, user_id) is None:
        raise HTTPException(404, "User not found")
    try:
        expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)
    except OverflowError as exc:
        raise ValueError("Token lifetime is too large") from exc
    secret = secrets.token_urlsafe(32)
    record = ApiToken(
        user_id=user_id,
        token_hash=hashlib.sha256(secret.encode("ascii")).hexdigest(),
        expires_at=expires_at,
    )
    session.add(record)
    session.flush()
    return record, secret


def revoke_token(session: Session, token_id: UUID) -> None:
    record = session.get(ApiToken, token_id)
    if record is None:
        raise HTTPException(404, "Token not found")
    if record.revoked_at is None:
        record.revoked_at = datetime.now(UTC)
        session.flush()


def grant_owner(session: Session, workspace_id: UUID, user_id: UUID) -> None:
    # Operator commands possess DB credentials, not a caller-supplied API identity.
    if (
        session.scalar(select(Workspace.id).where(Workspace.id == workspace_id).with_for_update())
        is None
    ):
        raise HTTPException(404, "Workspace not found")
    if session.get(User, user_id) is None:
        raise HTTPException(404, "User not found")
    session.execute(
        insert(WorkspaceMembership)
        .values(workspace_id=workspace_id, user_id=user_id, role="owner")
        .on_conflict_do_update(
            index_elements=[WorkspaceMembership.workspace_id, WorkspaceMembership.user_id],
            set_={"role": "owner"},
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create-user")
    create.add_argument("--name", required=True)
    issue = commands.add_parser("issue-token")
    issue.add_argument("--user-id", type=UUID, required=True)
    issue.add_argument("--expires-in-days", type=int, default=30)
    revoke = commands.add_parser("revoke-token")
    revoke.add_argument("--token-id", type=UUID, required=True)
    owner = commands.add_parser("grant-owner")
    owner.add_argument("--workspace-id", type=UUID, required=True)
    owner.add_argument("--user-id", type=UUID, required=True)
    args = parser.parse_args()
    engine = create_engine(Settings().database_url, hide_parameters=True)
    try:
        with Session(engine) as session, session.begin():
            result: dict[str, object]
            if args.command == "create-user":
                result = UserRead.model_validate(create_user(session, args.name)).model_dump(
                    mode="json"
                )
            elif args.command == "issue-token":
                record, secret = issue_token(session, args.user_id, args.expires_in_days)
                result = {
                    "id": str(record.id),
                    "user_id": str(record.user_id),
                    "token": secret,
                    "expires_at": record.expires_at.isoformat(),
                }
            elif args.command == "revoke-token":
                revoke_token(session, args.token_id)
                result = {"id": str(args.token_id), "revoked": True}
            else:
                grant_owner(session, args.workspace_id, args.user_id)
                result = {
                    "workspace_id": str(args.workspace_id),
                    "user_id": str(args.user_id),
                    "role": "owner",
                }
        # Nothing (especially credentials) is emitted until the transaction commits.
        print(json.dumps(result))
    except ValidationError:
        parser.exit(1, "Invalid user name\n")
    except (HTTPException, ValueError) as exc:
        parser.exit(1, f"{exc.detail if isinstance(exc, HTTPException) else exc}\n")
    except SQLAlchemyError:
        parser.exit(1, "Database unavailable\n")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
