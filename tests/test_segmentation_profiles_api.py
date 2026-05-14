import numpy as np
from fastapi.testclient import TestClient
from main import app
from segmentation import MapSegmenter
from session_manager import sessions


def _build_test_image() -> np.ndarray:
    image = np.zeros((120, 120, 3), dtype=np.uint8)
    image[:, :] = (240, 240, 240)
    image[10:90, 10:90] = (20, 20, 220)
    image[30:110, 30:110] = (20, 200, 20)
    return image


def test_segment_legacy_profile_is_default():
    image = _build_test_image()
    sessions["segment-session"] = {
        "width": image.shape[1],
        "height": image.shape[0],
        "regions": [],
        "segmenter": MapSegmenter(image),
    }
    client = TestClient(app)
    response = client.post(
        "/api/segment",
        json={"session_id": "segment-session", "n_colors": 4, "min_area": 20},
    )
    assert response.status_code == 200
    assert response.json()["profile"] == "legacy"


def test_segment_supports_robust_profile():
    image = _build_test_image()
    sessions["segment-session"] = {
        "width": image.shape[1],
        "height": image.shape[0],
        "regions": [],
        "segmenter": MapSegmenter(image),
    }
    client = TestClient(app)
    response = client.post(
        "/api/segment",
        json={
            "session_id": "segment-session",
            "n_colors": 4,
            "min_area": 20,
            "robust_mode": True,
            "robust_settings": {"text_suppression": True, "morphology_kernel": 5},
        },
    )
    assert response.status_code == 200
    assert response.json()["profile"] == "robust"


def test_segment_supports_contour_hardening_settings_opt_in():
    image = _build_test_image()
    sessions["segment-session"] = {
        "width": image.shape[1],
        "height": image.shape[0],
        "regions": [],
        "segmenter": MapSegmenter(image),
    }
    client = TestClient(app)
    response = client.post(
        "/api/segment",
        json={
            "session_id": "segment-session",
            "n_colors": 4,
            "min_area": 20,
            "robust_mode": True,
            "robust_settings": {
                "text_suppression": True,
                "morphology_kernel": 5,
                "contour_min_points": 5,
                "contour_solidity_min": 0.2,
                "contour_smoothing_epsilon_scale": 0.003,
                "artifact_min_component_area": 15,
            },
        },
    )
    assert response.status_code == 200
    assert response.json()["profile"] == "robust"
