"""
Structured operation logs and error dashboard store.
"""

from __future__ import annotations

import threading
import time
import uuid
from typing import Dict, List, Optional

from error_taxonomy import classify_error

_lock = threading.RLock()
_events: List[Dict] = []
_errors: List[Dict] = []


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def log_event(
    level: str,
    category: str,
    message: str,
    *,
    session_id: Optional[str] = None,
    job_id: Optional[str] = None,
    extra: Optional[Dict] = None,
) -> Dict:
    event = {
        "id": str(uuid.uuid4()),
        "ts": _now_iso(),
        "level": level,
        "category": category,
        "message": message,
        "session_id": session_id,
        "job_id": job_id,
        "extra": extra or {},
    }
    with _lock:
        _events.append(event)
        if len(_events) > 2000:
            del _events[: len(_events) - 2000]
    return event


def log_error(
    exc: Exception,
    *,
    session_id: Optional[str] = None,
    job_id: Optional[str] = None,
    stage: str = "runtime",
) -> Dict:
    code, domain = classify_error(exc)
    payload = log_event(
        "error",
        "exception",
        str(exc),
        session_id=session_id,
        job_id=job_id,
        extra={"code": code, "domain": domain, "stage": stage},
    )
    with _lock:
        _errors.append(payload)
        if len(_errors) > 1000:
            del _errors[: len(_errors) - 1000]
    return payload


def list_errors(limit: int = 100) -> List[Dict]:
    with _lock:
        return list(reversed(_errors[-max(1, limit) :]))


def list_events(limit: int = 100) -> List[Dict]:
    with _lock:
        return list(reversed(_events[-max(1, limit) :]))


def reset_ops_logs() -> None:
    with _lock:
        _events.clear()
        _errors.clear()
