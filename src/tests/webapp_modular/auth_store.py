"""
Simple in-memory auth/workspace store for product scaffolding.
"""

from __future__ import annotations

import hashlib
import secrets
import threading
import time
import uuid
from typing import Dict, List, Optional, Tuple

from config import AUTH_TOKEN_TTL_SECONDS

_lock = threading.RLock()
_users: Dict[str, Dict] = {}
_users_by_email: Dict[str, str] = {}
_tokens: Dict[str, Dict] = {}
_workspaces: Dict[str, Dict] = {}
_projects: Dict[str, Dict] = {}


def _now() -> float:
    return time.time()


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _hash_password(password: str, salt: str) -> str:
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    )
    return digest.hex()


def create_user(email: str, password: str, full_name: Optional[str] = None) -> Dict:
    email_key = _normalize_email(email)
    if len(password) < 8:
        raise ValueError("La password deve essere di almeno 8 caratteri")
    with _lock:
        if email_key in _users_by_email:
            raise ValueError("Email gia registrata")
        user_id = str(uuid.uuid4())
        salt = secrets.token_hex(16)
        user = {
            "id": user_id,
            "email": email_key,
            "full_name": (full_name or "").strip() or None,
            "password_salt": salt,
            "password_hash": _hash_password(password, salt),
            "created_at": _now(),
        }
        _users[user_id] = user
        _users_by_email[email_key] = user_id
        return _safe_user(user)


def authenticate_user(email: str, password: str) -> Optional[Dict]:
    email_key = _normalize_email(email)
    with _lock:
        user_id = _users_by_email.get(email_key)
        if not user_id:
            return None
        user = _users[user_id]
        candidate_hash = _hash_password(password, user["password_salt"])
        if not secrets.compare_digest(candidate_hash, user["password_hash"]):
            return None
        return _safe_user(user)


def issue_token(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    with _lock:
        _tokens[token] = {
            "user_id": user_id,
            "issued_at": _now(),
            "expires_at": _now() + AUTH_TOKEN_TTL_SECONDS,
        }
    return token


def _safe_user(user: Dict) -> Dict:
    return {
        "id": user["id"],
        "email": user["email"],
        "full_name": user.get("full_name"),
        "created_at": user["created_at"],
    }


def get_user_by_token(token: str) -> Optional[Dict]:
    with _lock:
        token_data = _tokens.get(token)
        if not token_data:
            return None
        if _now() > token_data["expires_at"]:
            del _tokens[token]
            return None
        user = _users.get(token_data["user_id"])
        if not user:
            return None
        return _safe_user(user)


def parse_bearer(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    if not authorization.lower().startswith("bearer "):
        return None
    token = authorization[7:].strip()
    return token or None


def create_workspace(owner_user_id: str, name: str) -> Dict:
    clean = name.strip()
    if len(clean) < 2:
        raise ValueError("Il nome workspace deve contenere almeno 2 caratteri")
    with _lock:
        workspace_id = str(uuid.uuid4())
        ws = {
            "id": workspace_id,
            "name": clean,
            "owner_user_id": owner_user_id,
            "created_at": _now(),
        }
        _workspaces[workspace_id] = ws
        return dict(ws)


def list_user_workspaces(user_id: str) -> List[Dict]:
    with _lock:
        return [dict(ws) for ws in _workspaces.values() if ws["owner_user_id"] == user_id]


def create_project(
    owner_user_id: str,
    workspace_id: str,
    name: str,
    description: Optional[str] = None,
) -> Dict:
    clean = name.strip()
    if len(clean) < 2:
        raise ValueError("Il nome progetto deve contenere almeno 2 caratteri")
    with _lock:
        workspace = _workspaces.get(workspace_id)
        if not workspace:
            raise ValueError("Workspace non trovato")
        if workspace["owner_user_id"] != owner_user_id:
            raise ValueError("Accesso workspace negato")
        project_id = str(uuid.uuid4())
        project = {
            "id": project_id,
            "workspace_id": workspace_id,
            "name": clean,
            "description": (description or "").strip() or None,
            "created_at": _now(),
        }
        _projects[project_id] = project
        return dict(project)


def list_workspace_projects(owner_user_id: str, workspace_id: str) -> List[Dict]:
    with _lock:
        workspace = _workspaces.get(workspace_id)
        if not workspace:
            raise ValueError("Workspace non trovato")
        if workspace["owner_user_id"] != owner_user_id:
            raise ValueError("Accesso workspace negato")
        return [dict(p) for p in _projects.values() if p["workspace_id"] == workspace_id]


def signup_with_default_workspace(
    email: str,
    password: str,
    full_name: Optional[str],
    workspace_name: str,
) -> Tuple[Dict, Dict, str]:
    user = create_user(email=email, password=password, full_name=full_name)
    workspace = create_workspace(owner_user_id=user["id"], name=workspace_name)
    token = issue_token(user["id"])
    return user, workspace, token


def reset_auth_state() -> None:
    with _lock:
        _users.clear()
        _users_by_email.clear()
        _tokens.clear()
        _workspaces.clear()
        _projects.clear()
