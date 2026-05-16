"""
CV-based semi-automatic georeferencing registration utilities.
"""

from __future__ import annotations

import base64
import math
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


def _compute_reprojection_error(
    src_to_ref: np.ndarray,
    src_points: np.ndarray,
    ref_points: np.ndarray,
) -> float:
    """Mean reprojection error in pixels for inlier correspondences."""
    projected = cv2.perspectiveTransform(
        src_points.reshape(-1, 1, 2).astype(np.float64),
        src_to_ref,
    ).reshape(-1, 2)
    diffs = projected - ref_points.reshape(-1, 2)
    errors = np.linalg.norm(diffs, axis=1)
    return float(np.mean(errors)) if len(errors) > 0 else float("inf")


def _compute_corner_sanity(
    src_to_ref: np.ndarray,
    source_w: int,
    source_h: int,
    ref_w: int,
    ref_h: int,
) -> Tuple[float, float]:
    """
    Returns:
    - in_frame_ratio: % of projected source corners inside reference frame.
    - area_ratio: projected quad area / reference area.
    """
    src_corners = np.array(
        [[0, 0], [source_w, 0], [source_w, source_h], [0, source_h]],
        dtype=np.float64,
    ).reshape(-1, 1, 2)
    projected = cv2.perspectiveTransform(src_corners, src_to_ref).reshape(-1, 2)
    inside = (
        (projected[:, 0] >= 0)
        & (projected[:, 0] <= ref_w - 1)
        & (projected[:, 1] >= 0)
        & (projected[:, 1] <= ref_h - 1)
    )
    in_frame_ratio = float(np.count_nonzero(inside) / 4.0)
    projected_area = cv2.contourArea(projected.astype(np.float32).reshape(-1, 1, 2))
    ref_area = float(max(ref_w * ref_h, 1))
    area_ratio = float(projected_area / ref_area)
    return in_frame_ratio, area_ratio


def _compute_geo_corner_ratio(
    src_to_geo: np.ndarray,
    source_w: int,
    source_h: int,
    bounds: Dict[str, float],
) -> Tuple[float, float, float]:
    """Corner in-bounds ratio + projected extent ratios in geo space."""
    src_corners = np.array(
        [[0, 0], [source_w, 0], [source_w, source_h], [0, source_h]],
        dtype=np.float64,
    ).reshape(-1, 1, 2)
    projected = cv2.perspectiveTransform(src_corners, src_to_geo).reshape(-1, 2)
    lon_span = max(bounds["east"] - bounds["west"], 1e-9)
    lat_span = max(bounds["north"] - bounds["south"], 1e-9)
    lon_margin = lon_span * 0.2
    lat_margin = lat_span * 0.2
    inside = (
        (projected[:, 0] >= bounds["west"] - lon_margin)
        & (projected[:, 0] <= bounds["east"] + lon_margin)
        & (projected[:, 1] >= bounds["south"] - lat_margin)
        & (projected[:, 1] <= bounds["north"] + lat_margin)
    )
    in_bounds_ratio = float(np.count_nonzero(inside) / 4.0)
    projected_lon_span = float(np.max(projected[:, 0]) - np.min(projected[:, 0]))
    projected_lat_span = float(np.max(projected[:, 1]) - np.min(projected[:, 1]))
    lon_extent_ratio = projected_lon_span / lon_span
    lat_extent_ratio = projected_lat_span / lat_span
    return in_bounds_ratio, lon_extent_ratio, lat_extent_ratio


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
    reproj_error_px = _compute_reprojection_error(src_to_ref, src_inliers, ref_inliers)

    ref_h, ref_w = ref_image.shape[:2]
    src_h, src_w = source_image.shape[:2]
    in_frame_ratio, area_ratio = _compute_corner_sanity(
        src_to_ref,
        source_w=src_w,
        source_h=src_h,
        ref_w=ref_w,
        ref_h=ref_h,
    )

    geo_points = np.array(
        [_ref_pixel_to_geo(float(x), float(y), ref_bounds, ref_w, ref_h) for x, y in ref_inliers],
        dtype=np.float64,
    ).reshape(-1, 1, 2)
    src_inliers_for_geo = src_inliers.astype(np.float64).reshape(-1, 1, 2)

    src_to_geo, geo_mask = cv2.findHomography(src_inliers_for_geo, geo_points, cv2.RANSAC, 1e-4)
    if src_to_geo is None:
        raise ValueError("Impossibile stimare omografia finale cv_auto (source->geo)")

    geo_corner_ratio, geo_lon_extent_ratio, geo_lat_extent_ratio = _compute_geo_corner_ratio(
        src_to_geo,
        source_w=src_w,
        source_h=src_h,
        bounds=ref_bounds,
    )
    if geo_corner_ratio < 0.5:
        raise ValueError("cv_auto sanity check fallito: geometria fuori bounds")
    if max(geo_lon_extent_ratio, geo_lat_extent_ratio) > 3.0:
        raise ValueError("cv_auto sanity check fallito: estensione geografica anomala")

    inlier_ratio = inlier_count / max(len(good), 1)
    match_score = min(1.0, len(good) / max(float(min_matches * 2), 1.0))
    reproj_score = math.exp(-max(reproj_error_px, 0.0) / 25.0)
    corner_score = 0.7 + 0.3 * max(0.0, min(1.0, in_frame_ratio))
    # Prefer transforms that keep projected footprint near realistic scale.
    area_score = math.exp(-abs(math.log(max(area_ratio, 1e-6))))
    confidence = inlier_ratio * match_score * reproj_score * corner_score * area_score
    metrics = {
        "mode": "cv_auto",
        "num_gcps": 0,
        "cv_total_matches": int(len(good)),
        "cv_inliers": inlier_count,
        "cv_inlier_ratio": round(float(inlier_ratio), 6),
        "cv_reprojection_error_px": round(float(reproj_error_px), 4),
        "cv_corner_in_frame_ratio": round(float(in_frame_ratio), 6),
        "cv_projected_area_ratio": round(float(area_ratio), 6),
        "cv_geo_corner_ratio": round(float(geo_corner_ratio), 6),
        "cv_geo_lon_extent_ratio": round(float(geo_lon_extent_ratio), 6),
        "cv_geo_lat_extent_ratio": round(float(geo_lat_extent_ratio), 6),
        "cv_confidence": round(float(confidence), 6),
        "cv_reference_size": {"width": ref_w, "height": ref_h},
        "cv_detector": best["name"],
        "rmse_degrees": 0.0,
        "rmse_meters": 0.0,
        "rmse_ratio": 0.0,
        "validated": True,
    }
    return src_to_geo, metrics
