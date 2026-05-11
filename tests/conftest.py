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

    sessions.clear()
    yield
    sessions.clear()
