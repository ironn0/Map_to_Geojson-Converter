import base64
from dataclasses import dataclass

import cv2
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


def test_export_supports_affine_gcps_and_quality_metadata():
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
            "bounds": {"north": 45, "south": 35, "east": 15, "west": 5},
            "georeferencing": {
                "mode": "affine",
                "gcps": [
                    {"pixel_x": 0, "pixel_y": 0, "lon": 5, "lat": 45},
                    {"pixel_x": 100, "pixel_y": 0, "lon": 15, "lat": 45},
                    {"pixel_x": 0, "pixel_y": 100, "lon": 5, "lat": 35},
                ],
            },
            "geometry_sanitize": {"enabled": True, "simplify_tolerance": 0.0},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["properties"]["georeferencing"]["mode"] == "affine"
    assert payload["features"][0]["properties"]["geometry_quality"]["sanitized"] is True


def test_export_cv_auto_fallbacks_safely_when_reference_not_matchable():
    blank = np.full((100, 100, 3), 255, dtype=np.uint8)
    ref = np.zeros((100, 100, 3), dtype=np.uint8)
    ok, encoded = cv2.imencode(".png", ref)
    assert ok
    ref_b64 = base64.b64encode(encoded.tobytes()).decode("ascii")

    sessions["session-test"] = {
        "width": 100,
        "height": 100,
        "image": blank,
        "regions": [FakeRegion(contour=_valid_contour(), area=1200.0, color=(10, 20, 30))],
    }
    client = TestClient(app)
    response = client.post(
        "/api/export",
        json={
            "session_id": "session-test",
            "bounds": {"north": 45, "south": 35, "east": 15, "west": 5},
            "georeferencing": {
                "mode": "cv_auto",
                "allow_fallback": True,
                "min_matches": 20,
                "confidence_threshold": 0.4,
                "cv_reference_image_base64": ref_b64,
                "cv_reference_bounds": {"north": 45, "south": 35, "east": 15, "west": 5},
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["properties"]["georeferencing"]["fallback_from"] == "cv_auto"
