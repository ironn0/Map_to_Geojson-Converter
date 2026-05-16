import numpy as np
from fastapi.testclient import TestClient
from main import app
from session_manager import sessions


def _circle_test_image() -> np.ndarray:
    image = np.full((220, 320, 3), 245, dtype=np.uint8)
    yy, xx = np.ogrid[:220, :320]
    cx, cy, r = 160, 110, 52
    ring = np.abs(np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) - r) <= 2
    image[ring] = (30, 30, 30)
    return image


def test_detect_circle_returns_geo_center_and_radius():
    image = _circle_test_image()
    sessions["circle-session"] = {
        "width": image.shape[1],
        "height": image.shape[0],
        "image": image,
        "regions": [],
    }
    client = TestClient(app)
    response = client.post(
        "/api/detect-circle",
        json={
            "session_id": "circle-session",
            "bounds": {"north": 46.0, "south": 40.0, "east": 16.0, "west": 8.0},
            "strict_center_target_m": 5.0,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert "geo_center" in payload["circle"]
    assert payload["circle"]["radius_m"] > 0
    assert payload["circle"]["accuracy_level"] in {"strict", "medium", "fallback"}


def test_export_includes_detected_circle_even_without_regions():
    image = _circle_test_image()
    sessions["circle-session"] = {
        "width": image.shape[1],
        "height": image.shape[0],
        "image": image,
        "regions": [],
        "detected_circle": {
            "geo_center": [12.0, 43.0],
            "radius_m": 2500.0,
            "radius_std_m": 40.0,
            "accuracy_level": "strict",
            "estimated_center_error_m": 5.0,
            "confidence": 0.9,
            "quality_metrics": {"edge_inlier_ratio": 0.7},
            "geojson_geometry": {
                "type": "Polygon",
                "coordinates": [[[12.0, 43.0], [12.01, 43.0], [12.0, 43.0]]],
            },
        },
    }
    client = TestClient(app)
    response = client.post(
        "/api/export",
        json={
            "session_id": "circle-session",
            "bounds": {"north": 46.0, "south": 40.0, "east": 16.0, "west": 8.0},
            "include_detected_circle": True,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    circle_features = [f for f in payload["features"] if f["properties"].get("type") == "detected-circle"]
    assert len(circle_features) == 1
