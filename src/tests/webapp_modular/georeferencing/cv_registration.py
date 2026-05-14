"""
CV-based semi-automatic georeferencing registration utilities.
"""

from __future__ import annotations

import base64
from typing import Any, Dict, Tuple

import cv2
import numpy as np


def _decode_base64_image(image_b64: str) -> np.ndarray:
    payload = image_b64.split(",", 1)[1] if image_b64.startswith("data:") else image_b64
    img_bytes = base64.b64decode(payload)
    nparr = np.frombuffer(img_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Impossibile decodificare cv_reference_image_base64")
    return image


def _ref_pixel_to_geo(x: float, y: float, bounds: Dict[str, float], width: int, height: int) -> Tuple[float, float]:
    lon = bounds["west"] + (x / width) * (bounds["east"] - bounds["west"])
    lat = bounds["north"] - (y / height) * (bounds["north"] - bounds["south"])
    return lon, lat


def build_cv_auto_transform(
    source_image: np.ndarray,
    georef_cfg: Dict[str, Any],
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Build source-pixel -> geo homography using CV feature matching
    against a georeferenced reference raster.
    """
    if source_image is None:
        raise ValueError("source_image mancante per cv_auto")

    ref_image = _decode_base64_image(georef_cfg["cv_reference_image_base64"])
    ref_bounds = georef_cfg["cv_reference_bounds"]
    if hasattr(ref_bounds, "model_dump"):
        ref_bounds = ref_bounds.model_dump()

    min_matches = int(georef_cfg.get("min_matches", 30))
    inlier_threshold = float(georef_cfg.get("inlier_threshold", 3.0))

    src_gray = cv2.cvtColor(source_image, cv2.COLOR_BGR2GRAY)
    ref_gray = cv2.cvtColor(ref_image, cv2.COLOR_BGR2GRAY)

    detector_specs = []
    if hasattr(cv2, "SIFT_create"):
        detector_specs.append(("SIFT", cv2.SIFT_create(nfeatures=4000), cv2.NORM_L2))
    detector_specs.append(("AKAZE", cv2.AKAZE_create(), cv2.NORM_HAMMING))
    detector_specs.append(("ORB", cv2.ORB_create(nfeatures=5000), cv2.NORM_HAMMING))

    best = None
    for detector_name, detector, norm in detector_specs:
        src_kp, src_desc = detector.detectAndCompute(src_gray, None)
        ref_kp, ref_desc = detector.detectAndCompute(ref_gray, None)
        if src_desc is None or ref_desc is None or len(src_kp) < 8 or len(ref_kp) < 8:
            continue

        bf = cv2.BFMatcher(norm, crossCheck=False)
        knn = bf.knnMatch(src_desc, ref_desc, k=2)
        good = []
        for pair in knn:
            if len(pair) < 2:
                continue
            m, n = pair
            if m.distance < 0.78 * n.distance:
                good.append(m)

        if best is None or len(good) > len(best["good"]):
            best = {"name": detector_name, "src_kp": src_kp, "ref_kp": ref_kp, "good": good}

    if best is None:
        raise ValueError("Feature insufficienti per cv_auto")

    src_kp = best["src_kp"]
    ref_kp = best["ref_kp"]
    good = best["good"]

    if len(good) < min_matches:
        raise ValueError(f"Match insufficienti per cv_auto ({len(good)} < {min_matches})")

    src_pts = np.float32([src_kp[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    ref_pts = np.float32([ref_kp[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

    src_to_ref, mask = cv2.findHomography(src_pts, ref_pts, cv2.RANSAC, inlier_threshold)
    if src_to_ref is None or mask is None:
        raise ValueError("Impossibile stimare omografia cv_auto (source->reference)")

    inlier_mask = mask.ravel().astype(bool)
    inlier_count = int(np.count_nonzero(inlier_mask))
    if inlier_count < 4:
        raise ValueError("Inlier insufficienti per cv_auto")

    src_inliers = src_pts[inlier_mask].reshape(-1, 2)
    ref_inliers = ref_pts[inlier_mask].reshape(-1, 2)

    ref_h, ref_w = ref_image.shape[:2]
    geo_points = np.array(
        [_ref_pixel_to_geo(float(x), float(y), ref_bounds, ref_w, ref_h) for x, y in ref_inliers],
        dtype=np.float64,
    ).reshape(-1, 1, 2)
    src_inliers_for_geo = src_inliers.astype(np.float64).reshape(-1, 1, 2)

    src_to_geo, geo_mask = cv2.findHomography(src_inliers_for_geo, geo_points, cv2.RANSAC, 1e-4)
    if src_to_geo is None:
        raise ValueError("Impossibile stimare omografia finale cv_auto (source->geo)")

    inlier_ratio = inlier_count / max(len(good), 1)
    confidence = inlier_ratio * min(1.0, len(good) / max(float(min_matches * 2), 1.0))
    metrics = {
        "mode": "cv_auto",
        "num_gcps": 0,
        "cv_total_matches": int(len(good)),
        "cv_inliers": inlier_count,
        "cv_inlier_ratio": round(float(inlier_ratio), 6),
        "cv_confidence": round(float(confidence), 6),
        "cv_reference_size": {"width": ref_w, "height": ref_h},
        "cv_detector": best["name"],
        "rmse_degrees": 0.0,
        "rmse_meters": 0.0,
        "rmse_ratio": 0.0,
        "validated": True,
    }
    return src_to_geo, metrics
