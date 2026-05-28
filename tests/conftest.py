import sys
from pathlib import Path

import pytest

WEBAPP_MODULAR_PATH = (
    Path(__file__).resolve().parents[1] / "src" / "tests" / "webapp_modular"
)
sys.path.insert(0, str(WEBAPP_MODULAR_PATH))


@pytest.fixture(autouse=True)
def clear_sessions():
    from session_manager import sessions
    try:
        from auth_store import reset_auth_state
    except Exception:
        reset_auth_state = None
    try:
        from billing_store import reset_billing_state
    except Exception:
        reset_billing_state = None
    try:
        from job_manager import reset_jobs
    except Exception:
        reset_jobs = None
    try:
        from ops_log import reset_ops_logs
    except Exception:
        reset_ops_logs = None

    sessions.clear()
    if reset_auth_state:
        reset_auth_state()
    if reset_billing_state:
        reset_billing_state()
    if reset_jobs:
        reset_jobs()
    if reset_ops_logs:
        reset_ops_logs()
    yield
    sessions.clear()
    if reset_auth_state:
        reset_auth_state()
    if reset_billing_state:
        reset_billing_state()
    if reset_jobs:
        reset_jobs()
    if reset_ops_logs:
        reset_ops_logs()
