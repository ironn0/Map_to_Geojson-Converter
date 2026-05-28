import time

import numpy as np
from fastapi.testclient import TestClient
from main import app
from segmentation import MapSegmenter
from session_manager import sessions


def _image() -> np.ndarray:
    image = np.full((120, 160, 3), 235, dtype=np.uint8)
    image[20:95, 30:120] = (50, 70, 180)
    return image


def _wait_job(client: TestClient, job_id: str, timeout_s: float = 3.0):
    start = time.time()
    while time.time() - start < timeout_s:
        res = client.get(f"/api/jobs/{job_id}")
        assert res.status_code == 200
        job = res.json()["job"]
        if job["status"] in {"completed", "failed"}:
            return job
        time.sleep(0.05)
    raise AssertionError("Job did not finish in time")


def test_queue_segment_job_completes_and_updates_session_regions():
    image = _image()
    sessions["jobs-session"] = {
        "width": image.shape[1],
        "height": image.shape[0],
        "image": image,
        "regions": [],
        "segmenter": MapSegmenter(image),
    }
    client = TestClient(app)
    start = client.post(
        "/api/jobs/segment",
        json={"session_id": "jobs-session", "n_colors": 30, "min_area": 200},
    )
    assert start.status_code == 200
    job_id = start.json()["job"]["id"]

    job = _wait_job(client, job_id)
    assert job["status"] == "completed"
    assert job["result"]["success"] is True
    assert len(sessions["jobs-session"]["regions"]) >= 1


def test_ops_errors_dashboard_collects_failed_job():
    image = _image()
    sessions["jobs-circle-fail"] = {
        "width": image.shape[1],
        "height": image.shape[0],
        "image": image,
        "regions": [],
        "segmenter": MapSegmenter(image),
    }
    client = TestClient(app)
    start = client.post(
        "/api/jobs/detect-circle",
        json={
            "session_id": "jobs-circle-fail",
            "bounds": {"north": 46.0, "south": 40.0, "east": 16.0, "west": 8.0},
            "strict_center_target_m": 5.0,
        },
    )
    assert start.status_code == 200
    job_id = start.json()["job"]["id"]
    job = _wait_job(client, job_id, timeout_s=5.0)
    assert job["status"] == "failed"

    errors = client.get("/api/ops/errors?limit=10")
    assert errors.status_code == 200
    payload = errors.json()["errors"]
    assert payload
    assert any(err["extra"]["code"] in {"PROCESSING_ERROR", "UNCLASSIFIED_ERROR"} for err in payload)
