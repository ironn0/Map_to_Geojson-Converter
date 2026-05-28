"""
Auth routes (signup/login/me) for product scaffolding.
"""

from typing import Dict

from auth_store import (
    authenticate_user,
    get_user_by_token,
    issue_token,
    parse_bearer,
    signup_with_default_workspace,
)
from fastapi import APIRouter, Header, HTTPException
from models import LoginRequest, SignupRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup")
async def signup(req: SignupRequest) -> Dict:
    try:
        user, workspace, token = signup_with_default_workspace(
            email=req.email,
            password=req.password,
            full_name=req.full_name,
            workspace_name=req.workspace_name,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"success": True, "token": token, "user": user, "workspace": workspace}


@router.post("/login")
async def login(req: LoginRequest) -> Dict:
    user = authenticate_user(req.email, req.password)
    if not user:
        raise HTTPException(401, "Credenziali non valide")
    token = issue_token(user["id"])
    return {"success": True, "token": token, "user": user}


@router.get("/me")
async def me(authorization: str = Header(default="", alias="Authorization")) -> Dict:
    token = parse_bearer(authorization)
    if not token:
        raise HTTPException(401, "Token mancante")
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(401, "Token non valido o scaduto")
    return {"success": True, "user": user}
