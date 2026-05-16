"""
Benchmark harness per conversioni difficili.

Run:
    python benchmarks/run_benchmark.py
"""

from __future__ import annotations

import base64
import json
import math
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

import cv2
import numpy as np
from shapely.geometry import Polygon

REPO_ROOT = Path(__file__).resolve().parents[1]
WEBAPP_MODULAR = REPO_ROOT / "src" / "tests" / "webapp_modular"
sys.path.insert(0, str(WEBAPP_MODULAR))

from georeferencing import (  # noqa: E402
    Georeferencer,
    detect_and_georeference_circle,
    sanitize_polygon_geometry,
)
from segmentation import MapSegmenter  # noqa: E402


def _load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _warp_points(points: List[List[float]], matrix: np.ndarray) -> np.ndarray:
    pts = np.array(points, dtype=np.float32).reshape(-1, 1, 2)
    return cv2.transform(pts, matrix).reshape(-1, 2)


def _build_fixture_image(
    case: Dict,
) -> Tuple[np.ndarray, List[Polygon], np.ndarray, List[Polygon], Dict | None]:
    image_cfg = case["image"]
    width = int(image_cfg["width"])
    height = int(image_cfg["height"])
    canvas = np.full((height, width, 3), 240, dtype=np.uint8)
    reference_canvas = np.full((height, width, 3), 240, dtype=np.uint8)

    center = (width / 2.0, height / 2.0)
    rotate = cv2.getRotationMatrix2D(center, float(image_cfg["rotation_degrees"]), 1.0)
    rotate[:, 2] += [float(image_cfg["skew_x"]) * width, 0.0]

    gt_polygons: List[Polygon] = []
    ref_polygons: List[Polygon] = []
    for region in case["regions"]:
        ref_pts = np.array(region["polygon"], dtype=np.float32)
        cv2.fillPoly(reference_canvas, [ref_pts.astype(np.int32).reshape(-1, 1, 2)], tuple(int(c) for c in region["color_bgr"]))
        ref_polygons.append(Polygon(ref_pts))

        warped = _warp_points(region["polygon"], rotate)
        pts_int = warped.astype(np.int32).reshape(-1, 1, 2)
        cv2.fillPoly(canvas, [pts_int], tuple(int(c) for c in region["color_bgr"]))
        gt_polygons.append(Polygon(warped))

    if image_cfg.get("add_text_labels", False):
        for idx, region in enumerate(case["regions"]):
            p = np.array(region["polygon"], dtype=np.float32)
            cx, cy = p[:, 0].mean(), p[:, 1].mean()
            cwx, cwy = _warp_points([[cx, cy]], rotate)[0]
            cv2.putText(
                canvas,
                f"R{idx+1}",
                (int(cwx) - 12, int(cwy)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (15, 15, 15),
                1,
                cv2.LINE_AA,
            )

    circle_gt = None
    if image_cfg.get("circle"):
        c = image_cfg["circle"]
        ref_center = np.array([[c["center"]]], dtype=np.float32)
        warped_center = _warp_points([c["center"]], rotate)[0]
        radius_px = float(c["radius_px"])
        color = tuple(int(v) for v in c.get("color_bgr", [40, 40, 40]))
        thickness = int(c.get("thickness", 2))
        cv2.circle(
            reference_canvas,
            (int(ref_center[0, 0, 0]), int(ref_center[0, 0, 1])),
            int(radius_px),
            color,
            thickness,
            lineType=cv2.LINE_AA,
        )
        cv2.circle(
            canvas,
            (int(warped_center[0]), int(warped_center[1])),
            int(radius_px),
            color,
            thickness,
            lineType=cv2.LINE_AA,
        )
        circle_gt = {
            "reference_center_px": (float(c["center"][0]), float(c["center"][1])),
            "warped_center_px": (float(warped_center[0]), float(warped_center[1])),
            "radius_px": radius_px,
        }

    noise_sigma = float(image_cfg["noise_sigma"])
    noise = np.random.default_rng(42).normal(0, noise_sigma, canvas.shape).astype(np.int16)
    noisy = np.clip(canvas.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return noisy, gt_polygons, reference_canvas, ref_polygons, circle_gt


def _polygon_iou(poly_a: Polygon, poly_b: Polygon) -> float:
    if poly_a.is_empty or poly_b.is_empty:
        return 0.0
    inter = poly_a.intersection(poly_b).area
    union = poly_a.union(poly_b).area
    if union <= 0:
        return 0.0
    return inter / union


def _match_polygons(preds: List[Polygon], refs: List[Polygon], threshold: float) -> List[Tuple[int, int, float]]:
    matches: List[Tuple[int, int, float]] = []
    used_pred = set()
    used_ref = set()
    while True:
        best = None
        for pi, pred in enumerate(preds):
            if pi in used_pred:
                continue
            for ri, ref in enumerate(refs):
                if ri in used_ref:
                    continue
                iou = _polygon_iou(pred, ref)
                if iou < threshold:
                    continue
                if best is None or iou > best[2]:
                    best = (pi, ri, iou)
        if best is None:
            break
        used_pred.add(best[0])
        used_ref.add(best[1])
        matches.append(best)
    return matches


def _centroid_distance_meters(geo: Georeferencer, poly_a: Polygon, poly_b: Polygon) -> float:
    ax, ay = poly_a.centroid.x, poly_a.centroid.y
    bx, by = poly_b.centroid.x, poly_b.centroid.y
    lon_a, lat_a = geo.pixel_to_coord(int(ax), int(ay))
    lon_b, lat_b = geo.pixel_to_coord(int(bx), int(by))
    mean_lat = math.radians((lat_a + lat_b) / 2.0)
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * math.cos(mean_lat)
    return math.sqrt(((lon_a - lon_b) * m_per_deg_lon) ** 2 + ((lat_a - lat_b) * m_per_deg_lat) ** 2)


def _pixel_to_geo(bounds: Dict, width: int, height: int, x: float, y: float) -> Tuple[float, float]:
    lon = bounds["west"] + (x / width) * (bounds["east"] - bounds["west"])
    lat = bounds["north"] - (y / height) * (bounds["north"] - bounds["south"])
    return lon, lat


def _distance_geo_meters(lon_a: float, lat_a: float, lon_b: float, lat_b: float) -> float:
    mean_lat = math.radians((lat_a + lat_b) / 2.0)
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * math.cos(mean_lat)
    return math.sqrt(((lon_a - lon_b) * m_per_deg_lon) ** 2 + ((lat_a - lat_b) * m_per_deg_lat) ** 2)


def run_case(case: Dict, thresholds: Dict) -> Dict:
    image, gt_polygons, reference_image, reference_polygons, circle_gt = _build_fixture_image(case)
    segmenter = MapSegmenter(image)

    start = time.perf_counter()
    regions = segmenter.segment(
        n_colors=4,
        min_area=600,
        robust_mode=True,
        robust_settings={"text_suppression": True},
    )
    elapsed = time.perf_counter() - start

    sorted_regions = sorted(regions, key=lambda r: r.area, reverse=True)
    candidate_regions = sorted_regions[: max(len(gt_polygons) + 1, 4)]

    pred_polygons: List[Polygon] = []
    for region in candidate_regions:
        coords = region.contour.reshape(-1, 2).tolist()
        try:
            geojson_geom, _ = sanitize_polygon_geometry(
                coords,
                min_polygon_area=220.0,
                simplify_tolerance=0.5,
                keep_multipolygons=False,
            )
        except Exception:
            continue
        if geojson_geom["type"] != "Polygon":
            continue
        pred_polygons.append(Polygon(geojson_geom["coordinates"][0]))

    iou_threshold = float(thresholds["iou_match_threshold"])
    matches = _match_polygons(pred_polygons, gt_polygons, iou_threshold)

    precision = len(matches) / len(pred_polygons) if pred_polygons else 0.0
    recall = len(matches) / len(gt_polygons) if gt_polygons else 0.0

    georef = Georeferencer(
        width=image.shape[1],
        height=image.shape[0],
        bounds=case["bounds"],
        georeferencing=case["georeferencing"],
    )
    spatial_errors = [
        _centroid_distance_meters(georef, pred_polygons[pi], gt_polygons[ri]) for pi, ri, _ in matches
    ]
    spatial_error = float(np.mean(spatial_errors)) if spatial_errors else float("inf")

    ref_ok, ref_buf = cv2.imencode(".png", reference_image)
    if not ref_ok:
        raise RuntimeError("Encoding reference image fallita")
    ref_b64 = base64.b64encode(ref_buf.tobytes()).decode("ascii")
    cv_auto_georef = Georeferencer(
        width=image.shape[1],
        height=image.shape[0],
        bounds=case["bounds"],
        georeferencing={
            "mode": "cv_auto",
            "allow_fallback": True,
            "min_matches": int(thresholds.get("cv_auto_min_matches", 20)),
            "inlier_threshold": float(thresholds.get("cv_auto_inlier_threshold", 3.0)),
            "confidence_threshold": float(thresholds.get("cv_auto_confidence_threshold", 0.2)),
            "cv_reference_image_base64": ref_b64,
            "cv_reference_bounds": case["bounds"],
        },
        source_image=image,
    )

    legacy_geo_errors = []
    cv_auto_geo_errors = []
    for pi, ri, _ in matches:
        pred_cent = pred_polygons[pi].centroid
        ref_cent = reference_polygons[ri].centroid
        target_lon, target_lat = _pixel_to_geo(
            case["bounds"],
            reference_image.shape[1],
            reference_image.shape[0],
            ref_cent.x,
            ref_cent.y,
        )
        legacy_lon, legacy_lat = georef.pixel_to_coord(int(pred_cent.x), int(pred_cent.y))
        cv_lon, cv_lat = cv_auto_georef.pixel_to_coord(int(pred_cent.x), int(pred_cent.y))
        legacy_geo_errors.append(_distance_geo_meters(legacy_lon, legacy_lat, target_lon, target_lat))
        cv_auto_geo_errors.append(_distance_geo_meters(cv_lon, cv_lat, target_lon, target_lat))

    legacy_geo_error = float(np.mean(legacy_geo_errors)) if legacy_geo_errors else float("inf")
    cv_auto_geo_error = float(np.mean(cv_auto_geo_errors)) if cv_auto_geo_errors else float("inf")
    cv_metrics = cv_auto_georef.get_transform_metrics()
    circle_center_error_m = None
    circle_radius_error_m = None
    if circle_gt is not None:
        circle_result = detect_and_georeference_circle(image, georef, strict_center_target_m=5.0)
        target_lon, target_lat = _pixel_to_geo(
            case["bounds"],
            reference_image.shape[1],
            reference_image.shape[0],
            circle_gt["warped_center_px"][0],
            circle_gt["warped_center_px"][1],
        )
        target_edge_lon, target_edge_lat = _pixel_to_geo(
            case["bounds"],
            reference_image.shape[1],
            reference_image.shape[0],
            circle_gt["warped_center_px"][0] + circle_gt["radius_px"],
            circle_gt["warped_center_px"][1],
        )
        pred_lon, pred_lat = circle_result["geo_center"]
        circle_center_error_m = _distance_geo_meters(pred_lon, pred_lat, target_lon, target_lat)
        target_radius_m = _distance_geo_meters(
            target_lon,
            target_lat,
            target_edge_lon,
            target_edge_lat,
        )
        circle_radius_error_m = abs(float(circle_result["radius_m"]) - float(target_radius_m))

    case_result = {
        "case": case["name"],
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "spatial_error_m": round(spatial_error, 2),
        "legacy_georef_error_m": round(legacy_geo_error, 2),
        "cv_auto_georef_error_m": round(cv_auto_geo_error, 2),
        "cv_auto_mode_used": cv_metrics.get("mode"),
        "cv_auto_confidence": cv_metrics.get("cv_confidence", None),
        "circle_center_error_m": round(circle_center_error_m, 2) if circle_center_error_m is not None else None,
        "circle_radius_error_m": round(circle_radius_error_m, 2) if circle_radius_error_m is not None else None,
        "conversion_time_s": round(elapsed, 3),
        "pred_polygons": len(pred_polygons),
        "gt_polygons": len(gt_polygons),
    }
    return case_result


def evaluate(results: List[Dict], thresholds: Dict) -> Tuple[bool, Dict]:
    mean_precision = float(np.mean([r["precision"] for r in results]))
    mean_recall = float(np.mean([r["recall"] for r in results]))
    mean_spatial_error = float(np.mean([r["spatial_error_m"] for r in results]))
    mean_time = float(np.mean([r["conversion_time_s"] for r in results]))
    mean_legacy_georef_error = float(np.mean([r["legacy_georef_error_m"] for r in results]))
    mean_cv_auto_georef_error = float(np.mean([r["cv_auto_georef_error_m"] for r in results]))

    center_errors = [r["circle_center_error_m"] for r in results if r.get("circle_center_error_m") is not None]
    radius_errors = [r["circle_radius_error_m"] for r in results if r.get("circle_radius_error_m") is not None]
    center_p50 = float(np.percentile(center_errors, 50)) if center_errors else None
    radius_p50 = float(np.percentile(radius_errors, 50)) if radius_errors else None

    summary = {
        "mean_precision": round(mean_precision, 4),
        "mean_recall": round(mean_recall, 4),
        "mean_spatial_error_m": round(mean_spatial_error, 2),
        "mean_conversion_time_s": round(mean_time, 3),
        "mean_legacy_georef_error_m": round(mean_legacy_georef_error, 2),
        "mean_cv_auto_georef_error_m": round(mean_cv_auto_georef_error, 2),
    }

    cv_auto_gain = mean_legacy_georef_error - mean_cv_auto_georef_error
    required_gain = float(thresholds.get("cv_auto_min_improvement_m", 1000.0))
    target_next_phase = float(
        thresholds.get("cv_auto_target_next_phase_m", required_gain),
    )
    passed = (
        mean_precision >= thresholds["min_precision"]
        and mean_recall >= thresholds["min_recall"]
        and mean_spatial_error <= thresholds["max_spatial_error_m"]
        and mean_time <= thresholds["max_conversion_time_s"]
        and cv_auto_gain >= required_gain
    )
    summary["cv_auto_gain_m"] = round(cv_auto_gain, 2)
    summary["cv_auto_min_required_gain_m"] = round(required_gain, 2)
    summary["cv_auto_next_phase_target_m"] = round(target_next_phase, 2)
    summary["cv_auto_next_phase_gap_m"] = round(target_next_phase - cv_auto_gain, 2)
    summary["cv_auto_next_phase_ready"] = bool(cv_auto_gain >= target_next_phase)
    if center_p50 is not None:
        summary["circle_center_error_p50_m"] = round(center_p50, 2)
    if radius_p50 is not None:
        summary["circle_radius_error_p50_m"] = round(radius_p50, 2)

    circle_center_gate = float(thresholds.get("circle_center_error_p50_max_m", 20.0))
    circle_radius_gate = float(thresholds.get("circle_radius_error_p50_max_m", 30.0))
    circle_ok = True
    if center_p50 is not None:
        circle_ok = circle_ok and center_p50 <= circle_center_gate
    if radius_p50 is not None:
        circle_ok = circle_ok and radius_p50 <= circle_radius_gate

    passed = passed and circle_ok
    summary["circle_gate_center_max_m"] = round(circle_center_gate, 2)
    summary["circle_gate_radius_max_m"] = round(circle_radius_gate, 2)
    summary["circle_gate_pass"] = bool(circle_ok)
    return passed, summary


def main() -> int:
    thresholds = _load_json(REPO_ROOT / "benchmarks" / "thresholds.json")
    fixture_paths = sorted((REPO_ROOT / "benchmarks" / "fixtures").glob("*.json"))
    if not fixture_paths:
        raise RuntimeError("Nessun fixture benchmark disponibile in benchmarks/fixtures")

    results = []
    for path in fixture_paths:
        case = _load_json(path)
        results.append(run_case(case, thresholds))

    passed, summary = evaluate(results, thresholds)

    print("=== Benchmark Results ===")
    for result in results:
        print(json.dumps(result, ensure_ascii=False))
    print("--- Summary ---")
    print(json.dumps(summary, ensure_ascii=False))
    print("--- Thresholds ---")
    print(json.dumps(thresholds, ensure_ascii=False))
    print(f"Status: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
