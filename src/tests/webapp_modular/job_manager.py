"""
Background job queue with retry/timeout and status tracking.
"""

from __future__ import annotations

import concurrent.futures
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from config import JOBS_DEFAULT_MAX_ATTEMPTS, JOBS_DEFAULT_TIMEOUT_S, JOBS_MAX_WORKERS
from ops_log import log_error, log_event

JobFn = Callable[[], Any]

_lock = threading.RLock()
_jobs: Dict[str, Dict] = {}
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=JOBS_MAX_WORKERS)


def _now() -> float:
    return time.time()


def _run_with_timeout(fn: JobFn, timeout_s: int) -> Any:
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as run_exec:
        future = run_exec.submit(fn)
        return future.result(timeout=timeout_s)


def _attempt_runner(job_id: str) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        job["status"] = "running"
        job["updated_at"] = _now()
        attempt_no = int(job["attempts"]) + 1
        job["attempts"] = attempt_no
    log_event(
        "info",
        "job",
        f"Job attempt {attempt_no} started",
        session_id=job.get("session_id"),
        job_id=job_id,
        extra={"job_type": job["type"]},
    )
    try:
        result = _run_with_timeout(job["fn"], int(job["timeout_s"]))
    except concurrent.futures.TimeoutError:
        exc = TimeoutError(f"Job timeout after {job['timeout_s']}s")
        _handle_attempt_error(job_id, exc)
        return
    except Exception as exc:  # noqa: BLE001
        _handle_attempt_error(job_id, exc)
        return

    with _lock:
        current = _jobs.get(job_id)
        if not current:
            return
        current["status"] = "completed"
        current["result"] = result
        current["updated_at"] = _now()
    log_event(
        "info",
        "job",
        "Job completed",
        session_id=job.get("session_id"),
        job_id=job_id,
        extra={"job_type": job["type"], "attempts": job["attempts"]},
    )


def _handle_attempt_error(job_id: str, exc: Exception) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        attempts = int(job["attempts"])
        max_attempts = int(job["max_attempts"])
        job["updated_at"] = _now()
    log_error(exc, session_id=job.get("session_id"), job_id=job_id, stage="job_attempt")
    if attempts < max_attempts:
        with _lock:
            job = _jobs.get(job_id)
            if not job:
                return
            job["status"] = "retrying"
        log_event(
            "warning",
            "job",
            "Retrying job after error",
            session_id=job.get("session_id"),
            job_id=job_id,
            extra={"attempts": attempts, "max_attempts": max_attempts},
        )
        _executor.submit(_attempt_runner, job_id)
        return

    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        job["status"] = "failed"
        job["error"] = str(exc)
        job["updated_at"] = _now()


def submit_job(
    *,
    job_type: str,
    session_id: Optional[str],
    fn: JobFn,
    max_attempts: int = JOBS_DEFAULT_MAX_ATTEMPTS,
    timeout_s: int = JOBS_DEFAULT_TIMEOUT_S,
) -> Dict:
    job_id = str(uuid.uuid4())
    payload = {
        "id": job_id,
        "type": job_type,
        "session_id": session_id,
        "status": "queued",
        "attempts": 0,
        "max_attempts": int(max_attempts),
        "timeout_s": int(timeout_s),
        "created_at": _now(),
        "updated_at": _now(),
        "result": None,
        "error": None,
        "fn": fn,
    }
    with _lock:
        _jobs[job_id] = payload
    log_event(
        "info",
        "job",
        "Job queued",
        session_id=session_id,
        job_id=job_id,
        extra={"job_type": job_type},
    )
    _executor.submit(_attempt_runner, job_id)
    return _public_job(payload)


def _public_job(job: Dict) -> Dict:
    return {
        "id": job["id"],
        "type": job["type"],
        "session_id": job["session_id"],
        "status": job["status"],
        "attempts": job["attempts"],
        "max_attempts": job["max_attempts"],
        "timeout_s": job["timeout_s"],
        "created_at": job["created_at"],
        "updated_at": job["updated_at"],
        "result": job["result"],
        "error": job["error"],
    }


def get_job(job_id: str) -> Optional[Dict]:
    with _lock:
        job = _jobs.get(job_id)
        return _public_job(job) if job else None


def list_jobs(session_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
    with _lock:
        values = list(_jobs.values())
    if session_id:
        values = [j for j in values if j.get("session_id") == session_id]
    values.sort(key=lambda x: x["created_at"], reverse=True)
    return [_public_job(j) for j in values[: max(1, limit)]]


def reset_jobs() -> None:
    with _lock:
        _jobs.clear()
