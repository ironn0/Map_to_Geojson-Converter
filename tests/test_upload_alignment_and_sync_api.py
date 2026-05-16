import io
from dataclasses import dataclass

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from main import app
from segmentation import MapSegmenter
from session_manager import sessions


@dataclass
class FakeRegion:
    contour: np.ndarray
    area: float
    color: tuple
    centroid: tuple = (30.0, 30.0)
    bbox: tuple = (10, 10, 20, 20)
    name: str = "TestRegion"


def _test_image() -> np.ndarray:
    image = np.full((80, 80, 3), 220, dtype=np.uint8)
    image[10:40, 10:40] = (40, 80, 200)
    return image


def _encode_png_bytes(image: np.ndarray) -> bytes:
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    return encoded.tobytes()


def _valid_contour() -> np.ndarray:
    return np.array([[[10, 10]], [[60, 10]], [[60, 60]], [[10, 60]]], dtype=np.float32)


def test_upload_rejects_oversized_payload():
    client = TestClient(app)
    oversized = b"\x00" * (10 * 1024 * 1024 + 1)
    response = client.post(
        "/api/upload",
        files={"file": ("huge.png", io.BytesIO(oversized), "image/png")},
    )
    assert response.status_code == 413


def test_upload_accepts_valid_png():
    client = TestClient(app)
    image = _test_image()
    payload = _encode_png_bytes(image)
    response = client.post(
        "/api/upload",
        files={"file": ("ok.png", io.BytesIO(payload), "image/png")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["width"] == image.shape[1]
    assert body["height"] == image.shape[0]
    assert body["session_id"] in sessions


def test_upload_accepts_octet_stream_if_extension_is_valid():
    client = TestClient(app)
    image = _test_image()
    payload = _encode_png_bytes(image)
    response = client.post(
        "/api/upload",
        files={"file": ("camera-export.jpg", io.BytesIO(payload), "application/octet-stream")},
    )
    assert response.status_code == 200
    assert response.json()["session_id"] in sessions


def test_upload_rejects_non_image_even_with_octet_stream():
    client = TestClient(app)
    response = client.post(
        "/api/upload",
        files={"file": ("not_image.txt", io.BytesIO(b"hello-world"), "application/octet-stream")},
    )
    assert response.status_code == 400


def test_upload_reference_invalid_geojson_type_returns_400():
    client = TestClient(app)
    response = client.post(
        "/api/upload-reference",
        files={"file": ("bad.geojson", io.BytesIO(b'{"type":"Invalid"}'), "application/json")},
    )
    assert response.status_code == 400


def test_add_and_update_region_are_reflected_in_export():
    image = _test_image()
    segmenter = MapSegmenter(image)
    sessions["sync-session"] = {
        "width": image.shape[1],
        "height": image.shape[0],
        "image": image,
        "regions": [FakeRegion(contour=_valid_contour(), area=900.0, color=(10, 20, 30))],
        "segmenter": segmenter,
    }
    client = TestClient(app)

    add_resp = client.post(
        "/api/add-region",
        json={
            "session_id": "sync-session",
            "points": [[20, 20], [30, 20], [30, 30], [20, 30]],
            "name": "Added",
            "color": "#00ff00",
        },
    )
    assert add_resp.status_code == 200
    assert len(add_resp.json()["regions"]) == 2

    update_resp = client.post(
        "/api/update-region",
        json={
            "session_id": "sync-session",
            "region_id": 0,
            "points": [[5, 5], [70, 5], [70, 70], [5, 70]],
        },
    )
    assert update_resp.status_code == 200

    export_resp = client.post(
        "/api/export",
        json={
            "session_id": "sync-session",
            "bounds": {"north": 45, "south": 35, "east": 15, "west": 5},
        },
    )
    assert export_resp.status_code == 200
    payload = export_resp.json()
    assert len(payload["features"]) == 2
    first_ring = payload["features"][0]["geometry"]["coordinates"][0]
    assert first_ring[0][0] == pytest.approx(5.625, abs=1e-6)  # lon from x=5 on width=80
