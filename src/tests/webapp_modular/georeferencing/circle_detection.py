"""
Circle detection and georeferencing utilities.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from .georeferencer import Georeferencer


def _haversine_m(lon_a: float, lat_a: float, lon_b: float, lat_b: float) -> float:
    r = 6_371_008.8
    phi1 = math.radians(lat_a)
    phi2 = math.radians(lat_b)
    d_phi = math.radians(lat_b - lat_a)
    d_lambda = math.radians(lon_b - lon_a)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(max(1e-12, 1 - a)))
    return r * c


def _circle_polygon_geo(
    georef: Georeferencer,
    center_x: float,
    center_y: float,
    radius_px: float,
    segments: int = 96,
) -> List[List[float]]:
    coords: List[List[float]] = []
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        px = center_x + radius_px * math.cos(angle)
        py = center_y + radius_px * math.sin(angle)
        lon, lat = georef.pixel_to_coord(int(round(px)), int(round(py)))
        coords.append([lon, lat])
    if coords:
        coords.append(coords[0][:])
    return coords


def _radius_stats_m(
    georef: Georeferencer,
    center_x: float,
    center_y: float,
    radius_px: float,
    samples: int = 48,
) -> Tuple[float, float]:
    lon_c, lat_c = georef.pixel_to_coord(int(round(center_x)), int(round(center_y)))
    dists: List[float] = []
    for i in range(samples):
        angle = 2 * math.pi * i / samples
        px = center_x + radius_px * math.cos(angle)
        py = center_y + radius_px * math.sin(angle)
        lon_p, lat_p = georef.pixel_to_coord(int(round(px)), int(round(py)))
        dists.append(_haversine_m(lon_c, lat_c, lon_p, lat_p))
    if not dists:
        return 0.0, 0.0
    return float(np.mean(dists)), float(np.std(dists))


def _estimate_circle_quality(
    edges: np.ndarray,
    center_x: float,
    center_y: float,
    radius_px: float,
) -> Dict[str, float]:
    h, w = edges.shape[:2]
    samples = 180
    inlier = 0
    for i in range(samples):
        angle = 2 * math.pi * i / samples
        x = int(round(center_x + radius_px * math.cos(angle)))
        y = int(round(center_y + radius_px * math.sin(angle)))
        if 0 <= x < w and 0 <= y < h and edges[y, x] > 0:
            inlier += 1
    edge_inlier_ratio = inlier / samples

    # Penalize circles that are too close to border.
    border_margin = min(center_x, center_y, w - center_x, h - center_y) / max(radius_px, 1.0)
    border_score = max(0.0, min(1.0, border_margin / 1.2))

    confidence = edge_inlier_ratio * border_score
    return {
        "edge_inlier_ratio": float(edge_inlier_ratio),
        "border_score": float(border_score),
        "pixel_confidence": float(confidence),
    }


def detect_circle_pixels(
    image: np.ndarray,
    min_radius_px: int = 8,
    max_radius_px: Optional[int] = None,
) -> Tuple[Tuple[float, float, float], Dict[str, float]]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (9, 9), 1.2)
    edges = cv2.Canny(blur, 60, 140)
    h, w = gray.shape[:2]
    if max_radius_px is None:
        max_radius_px = max(16, int(min(h, w) * 0.45))

    circles = cv2.HoughCircles(
        blur,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=max(20, int(min(h, w) * 0.15)),
        param1=120,
        param2=26,
        minRadius=int(min_radius_px),
        maxRadius=int(max_radius_px),
    )
    if circles is None or len(circles[0]) == 0:
        raise ValueError("Nessun cerchio rilevato")

    best_circle = None
    best_metrics = None
    for cx, cy, r in circles[0]:
        metrics = _estimate_circle_quality(edges, float(cx), float(cy), float(r))
        if best_metrics is None or metrics["pixel_confidence"] > best_metrics["pixel_confidence"]:
            best_metrics = metrics
            best_circle = (float(cx), float(cy), float(r))

    if best_circle is None or best_metrics is None:
        raise ValueError("Rilevamento cerchio non stabile")
    if best_metrics["edge_inlier_ratio"] < 0.18:
        raise ValueError("Cerchio troppo debole (edge_inlier_ratio basso)")

    return best_circle, best_metrics


def detect_and_georeference_circle(
    image: np.ndarray,
    georef: Georeferencer,
    strict_center_target_m: float = 5.0,
) -> Dict[str, Any]:
    (cx, cy, radius_px), metrics = detect_circle_pixels(image)
    lon_c, lat_c = georef.pixel_to_coord(int(round(cx)), int(round(cy)))
    radius_m, radius_std_m = _radius_stats_m(georef, cx, cy, radius_px)
    polygon_coords = _circle_polygon_geo(georef, cx, cy, radius_px)

    transform = georef.get_transform_metrics()
    cv_conf = float(transform.get("cv_confidence", 0.0)) if transform.get("mode") == "cv_auto" else 0.0
    transform_quality = 1.0 if transform.get("mode") in ("affine", "homography", "cv_auto") else 0.75
    if transform.get("fallback_from") == "cv_auto":
        transform_quality = 0.65

    confidence = (
        metrics["pixel_confidence"] * 0.55
        + max(cv_conf, 0.3 if transform.get("mode") in ("affine", "homography") else 0.0) * 0.30
        + transform_quality * 0.15
    )
    confidence = float(max(0.0, min(1.0, confidence)))

    # Conservative accuracy ladder: start strict, degrade if needed.
    if confidence >= 0.80:
        accuracy_level = "strict"
        estimated_center_error_m = strict_center_target_m
    elif confidence >= 0.60:
        accuracy_level = "medium"
        estimated_center_error_m = max(strict_center_target_m * 4, 20.0)
    else:
        accuracy_level = "fallback"
        estimated_center_error_m = max(strict_center_target_m * 10, 50.0)

    return {
        "pixel_center": [round(cx, 3), round(cy, 3)],
        "pixel_radius": round(radius_px, 3),
        "geo_center": [round(lon_c, 7), round(lat_c, 7)],
        "radius_m": round(radius_m, 3),
        "radius_std_m": round(radius_std_m, 3),
        "accuracy_level": accuracy_level,
        "estimated_center_error_m": round(estimated_center_error_m, 3),
        "confidence": round(confidence, 6),
        "quality_metrics": {
            "edge_inlier_ratio": round(metrics["edge_inlier_ratio"], 6),
            "border_score": round(metrics["border_score"], 6),
            "pixel_confidence": round(metrics["pixel_confidence"], 6),
            "transform_mode": transform.get("mode"),
            "transform_fallback": transform.get("fallback_from"),
            "cv_confidence": transform.get("cv_confidence"),
        },
        "geojson_geometry": {
            "type": "Polygon",
            "coordinates": [polygon_coords],
        },
    }
