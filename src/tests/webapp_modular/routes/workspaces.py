"""
Workspace and project routes for product scaffolding.
"""

from typing import Dict

from auth_store import (
    create_project,
    create_workspace,
    get_user_by_token,
    list_user_workspaces,
    list_workspace_projects,
    parse_bearer,
)
from fastapi import APIRouter, Header, HTTPException
from models import ProjectCreateRequest, WorkspaceCreateRequest

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


def _require_user(authorization: str) -> Dict:
    token = parse_bearer(authorization)
    if not token:
        raise HTTPException(401, "Token mancante")
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(401, "Token non valido o scaduto")
    return user


@router.get("")
async def get_workspaces(authorization: str = Header(default="", alias="Authorization")) -> Dict:
    user = _require_user(authorization)
    items = list_user_workspaces(user["id"])
    return {"success": True, "workspaces": items}


@router.post("")
async def create_new_workspace(
    req: WorkspaceCreateRequest,
    authorization: str = Header(default="", alias="Authorization"),
) -> Dict:
    user = _require_user(authorization)
    try:
        workspace = create_workspace(owner_user_id=user["id"], name=req.name)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"success": True, "workspace": workspace}


@router.get("/{workspace_id}/projects")
async def get_projects(
    workspace_id: str,
    authorization: str = Header(default="", alias="Authorization"),
) -> Dict:
    user = _require_user(authorization)
    try:
        projects = list_workspace_projects(owner_user_id=user["id"], workspace_id=workspace_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"success": True, "projects": projects}


@router.post("/{workspace_id}/projects")
async def create_new_project(
    workspace_id: str,
    req: ProjectCreateRequest,
    authorization: str = Header(default="", alias="Authorization"),
) -> Dict:
    user = _require_user(authorization)
    try:
        project = create_project(
            owner_user_id=user["id"],
            workspace_id=workspace_id,
            name=req.name,
            description=req.description,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"success": True, "project": project}
