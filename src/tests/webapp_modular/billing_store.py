"""
In-memory billing and quota metering store (Stripe-ready scaffolding).
"""

from __future__ import annotations

import threading
import time
from typing import Dict, Optional

from auth_store import get_user_by_token, parse_bearer
from config import PLAN_LIMITS

_lock = threading.RLock()
_user_plans: Dict[str, str] = {}
_usage: Dict[str, Dict[str, Dict[str, int]]] = {}


def _cycle_key(ts: Optional[float] = None) -> str:
    value = time.gmtime(ts or time.time())
    return f"{value.tm_year:04d}-{value.tm_mon:02d}"


def _ensure_plan(user_id: str) -> str:
    plan = _user_plans.get(user_id)
    if plan not in PLAN_LIMITS:
        plan = "free"
        _user_plans[user_id] = plan
    return plan


def get_plan_summary(user_id: str) -> Dict:
    with _lock:
        plan = _ensure_plan(user_id)
        cycle = _cycle_key()
        usage = _usage.setdefault(user_id, {}).setdefault(cycle, {})
        limits = PLAN_LIMITS[plan]
        return {
            "plan": plan,
            "cycle": cycle,
            "limits": dict(limits),
            "usage": {k: int(usage.get(k, 0)) for k in limits.keys()},
        }


def set_user_plan(user_id: str, plan: str) -> Dict:
    if plan not in PLAN_LIMITS:
        raise ValueError(f"Piano non supportato: {plan}")
    with _lock:
        _user_plans[user_id] = plan
        return get_plan_summary(user_id)


def consume_quota(authorization: str, metric: str, amount: int = 1) -> Optional[Dict]:
    token = parse_bearer(authorization)
    if not token:
        return None
    user = get_user_by_token(token)
    if not user:
        return None
    user_id = user["id"]
    with _lock:
        plan = _ensure_plan(user_id)
        limits = PLAN_LIMITS[plan]
        if metric not in limits:
            raise ValueError(f"Metrica non supportata: {metric}")
        cycle = _cycle_key()
        user_usage = _usage.setdefault(user_id, {}).setdefault(cycle, {})
        current = int(user_usage.get(metric, 0))
        limit = int(limits[metric])
        if current + amount > limit:
            raise PermissionError(
                f"Quota superata per '{metric}': {current}/{limit}. Upgrade piano richiesto."
            )
        user_usage[metric] = current + amount
        return {
            "user_id": user_id,
            "plan": plan,
            "metric": metric,
            "used": user_usage[metric],
            "limit": limit,
            "cycle": cycle,
        }


def user_from_auth(authorization: str) -> Optional[Dict]:
    token = parse_bearer(authorization)
    if not token:
        return None
    return get_user_by_token(token)


def reset_billing_state() -> None:
    with _lock:
        _user_plans.clear()
        _usage.clear()
