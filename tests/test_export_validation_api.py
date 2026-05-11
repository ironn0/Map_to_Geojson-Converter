from dataclasses import dataclass

import numpy as np
from fastapi.testclient import TestClient
from main import app
from session_manager import sessions


@dataclass
class FakeRegion:
    contour: np.ndarray
    area: float
    color: tuple
    name: str = "TestRegion"


def _valid_contour():
    return np.array([[[10, 10]], [[80, 10]], [[80, 80]], [[10, 80]]], dtype=np.int32)


def test_export_rejects_invalid_bounds():
    sessions["session-test"] = {
        "width": 100,
        "height": 100,
        "regions": [FakeRegion(contour=_valid_contour(), area=1200.0, color=(10, 20, 30))],
    }

    client = TestClient(app)
    response = client.post(
        "/api/export",
        json={
            "session_id": "session-test",
            "bounds": {"north": 30, "south": 40, "east": 15, "west": 5},
        },
    )

    assert response.status_code == 422


def test_export_rejects_invalid_contour():
    sessions["session-test"] = {
        "width": 100,
        "height": 100,
        "regions": [FakeRegion(contour=np.array([], dtype=np.int32), area=0.0, color=(0, 0, 0))],
    }

    client = TestClient(app)
    response = client.post(
        "/api/export",
        json={
            "session_id": "session-test",
            "bounds": {"north": 45, "south": 35, "east": 15, "west": 5},
        },
    )

    assert response.status_code == 400
    assert "Contorno non valido" in response.json()["detail"]
