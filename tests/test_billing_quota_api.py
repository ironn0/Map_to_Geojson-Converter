import io

import cv2
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


def _auth_headers() -> dict:
    client = TestClient(app)
    signup = client.post(
        "/api/auth/signup",
        json={
            "email": "quota@example.com",
            "password": "quota-pass-123",
            "workspace_name": "Quota WS",
        },
    )
    token = signup.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_billing_me_and_checkout_scaffold():
    client = TestClient(app)
    auth = _auth_headers()
    me = client.get("/api/billing/me", headers=auth)
    assert me.status_code == 200
    assert me.json()["billing"]["plan"] == "free"

    checkout = client.post(
        "/api/billing/checkout",
        json={"target_plan": "pro"},
        headers=auth,
    )
    assert checkout.status_code == 200
    assert "checkout.stripe.com" in checkout.json()["checkout_url"]


def test_circle_detection_quota_enforced_for_free_plan():
    client = TestClient(app)
    auth = _auth_headers()
    image = _circle_test_image()
    sessions["quota-session"] = {
        "width": image.shape[1],
        "height": image.shape[0],
        "image": image,
        "regions": [],
    }
    payload = {
        "session_id": "quota-session",
        "bounds": {"north": 46.0, "south": 40.0, "east": 16.0, "west": 8.0},
        "strict_center_target_m": 5.0,
    }
    # free plan limit for circle_detections = 3
    assert client.post("/api/detect-circle", json=payload, headers=auth).status_code == 200
    assert client.post("/api/detect-circle", json=payload, headers=auth).status_code == 200
    assert client.post("/api/detect-circle", json=payload, headers=auth).status_code == 200
    over = client.post("/api/detect-circle", json=payload, headers=auth)
    assert over.status_code == 429


def test_upload_quota_consumed_for_authenticated_user():
    client = TestClient(app)
    auth = _auth_headers()
    img = np.full((64, 64, 3), 200, dtype=np.uint8)
    ok, encoded = cv2.imencode(".png", img)
    assert ok
    upload = client.post(
        "/api/upload",
        files={"file": ("tiny.png", io.BytesIO(encoded.tobytes()), "image/png")},
        headers=auth,
    )
    assert upload.status_code == 200
    bill = client.get("/api/billing/me", headers=auth)
    assert bill.status_code == 200
    assert bill.json()["billing"]["usage"]["uploads"] == 1
