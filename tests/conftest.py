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

    sessions.clear()
    if reset_auth_state:
        reset_auth_state()
    if reset_billing_state:
        reset_billing_state()
    yield
    sessions.clear()
    if reset_auth_state:
        reset_auth_state()
    if reset_billing_state:
        reset_billing_state()
