"""Workspace permissions shared by API handlers and knowledge services."""

from typing import cast
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from pmknowledge.auth import Principal
from pmknowledge.models import User, Workspace, WorkspaceMembership
from pmknowledge.schemas import MembershipRead, WorkspaceRole

ROLE_LEVEL = {"reader": 0, "editor": 1, "owner": 2}


def require_workspace_access(
    session: Session, workspace_id: UUID, principal: Principal, minimum: WorkspaceRole = "reader"
) -> WorkspaceRole:
    role = session.scalar(
        select(WorkspaceMembership.role).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == principal.user_id,
        )
    )
    if role is None:
        raise HTTPException(404, "Workspace not found")
    if ROLE_LEVEL[role] < ROLE_LEVEL[minimum]:
        raise HTTPException(403, "Insufficient workspace permissions")
    return cast(WorkspaceRole, role)


def lock_owned_workspace(session: Session, workspace_id: UUID, principal: Principal) -> None:
    require_workspace_access(session, workspace_id, principal, "owner")
    session.execute(select(Workspace.id).where(Workspace.id == workspace_id).with_for_update())
    # A previous writer may have revoked/demoted this actor while this request waited.
    require_workspace_access(session, workspace_id, principal, "owner")


def change_membership(
    session: Session,
    workspace_id: UUID,
    principal: Principal,
    user_id: UUID,
    role: WorkspaceRole | None,
) -> MembershipRead | None:
    lock_owned_workspace(session, workspace_id, principal)
    if session.get(User, user_id) is None:
        raise HTTPException(404, "User not found")
    member = session.get(WorkspaceMembership, (workspace_id, user_id))
    if member is None and role is None:
        raise HTTPException(404, "Membership not found")
    if member is not None and member.role == "owner" and role != "owner":
        owners = session.scalar(
            select(func.count())
            .select_from(WorkspaceMembership)
            .where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.role == "owner",
            )
        )
        if owners == 1:
            raise HTTPException(409, "Workspace must retain an owner")
    if role is None:
        session.delete(member)
        session.flush()
        return None
    if member is None:
        member = WorkspaceMembership(workspace_id=workspace_id, user_id=user_id, role=role)
        session.add(member)
    else:
        member.role = role
    session.flush()
    return MembershipRead.model_validate(member)
