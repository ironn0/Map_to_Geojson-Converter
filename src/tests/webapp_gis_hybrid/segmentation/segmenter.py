"""Advanced OpenCV segmentation with geometric filtering and debug reports.

This module keeps the old ``MapSegmenter`` surface while adding a stricter
``AdvancedSegmenter``. It is intended as a drop-in candidate for the modular
webapp after validation.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

try:
    from models import ExtractedRegion
except ImportError:  # pragma: no cover - package import path
    from ..models import ExtractedRegion


class AdvancedSegmenter:
    """Segment map overlays while rejecting labels, lines and noisy fragments."""

    def __init__(
        self,
        image: np.ndarray,
        min_area_ratio: float = 0.001,
        max_aspect_ratio: float = 4.0,
        debug: bool = False,
    ):
        self.image = image
        self.height, self.width = image.shape[:2]
        self.total_area = float(self.width * self.height)
        self.min_area_ratio = min_area_ratio
        self.max_aspect_ratio = max_aspect_ratio
        self.debug = debug
        self.debug_log: List[Dict] = []
        self.regions: List[ExtractedRegion] = []
        self.edges = None
        self._contour_counter = 0
        self._preprocess()

    def _preprocess(self) -> None:
        """Build an edge image useful for diagnostics and future refinements."""
        gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        filtered = cv2.bilateralFilter(gray, 9, 75, 75)
        self.edges = cv2.Canny(filtered, 50, 150)
        self.edges = cv2.dilate(self.edges, np.ones((2, 2), np.uint8), iterations=1)

    def segment(self, n_colors: int = 40, min_area: int = 500) -> List[ExtractedRegion]:
        """Segment likely territories using overlay extraction, then K-Means fallback."""
        self.debug_log = []
        self._contour_counter = 0

        overlay_regions = self._segment_colored_overlays(min_area)
        if overlay_regions:
            overlay_regions.sort(key=lambda region: region.area, reverse=True)
            self.regions = overlay_regions
            return overlay_regions

        lab = cv2.cvtColor(self.image, cv2.COLOR_BGR2LAB)
        pixels = lab.reshape((-1, 3)).astype(np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
        _, labels, _ = cv2.kmeans(
            pixels,
            n_colors,
            None,
            criteria,
            10,
            cv2.KMEANS_PP_CENTERS,
        )

        regions = []
        for color_idx in range(n_colors):
            mask = (labels.flatten() == color_idx).reshape((self.height, self.width))
            mask = mask.astype(np.uint8) * 255
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                region = self._process_contour(contour, min_area)
                if region:
                    regions.append(region)

        regions = self._remove_overlapping(regions)
        regions.sort(key=lambda region: region.area, reverse=True)
        self.regions = regions
        return regions

    def _segment_colored_overlays(self, min_area: int) -> List[ExtractedRegion]:
        """Group saturated overlay colors and extract only their external contour."""
        hsv = cv2.cvtColor(self.image, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)
        min_overlay_area = max(float(min_area), self.total_area * self.min_area_ratio)
        color_mask = ((s > 35) & (v > 45)).astype(np.uint8) * 255

        regions: List[ExtractedRegion] = []
        close_size = max(9, int(min(self.width, self.height) * 0.025))
        if close_size % 2 == 0:
            close_size += 1
        close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close_size, close_size))
        open_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

        for start in range(0, 180, 15):
            hue_mask = (((h >= start) & (h < start + 15)).astype(np.uint8) * 255)
            mask = cv2.bitwise_and(color_mask, hue_mask)
            if cv2.countNonZero(mask) < min_overlay_area:
                continue

            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, close_kernel, iterations=2)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, open_kernel, iterations=1)
            mask = self._fill_mask_holes(mask)

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                region = self._process_contour(
                    contour,
                    int(min_overlay_area),
                    allow_low_saturation=True,
                )
                if region:
                    regions.append(region)

        return self._remove_overlapping(regions, overlap_threshold=0.45)

    def _fill_mask_holes(self, mask: np.ndarray) -> np.ndarray:
        """Fill internal holes without creating nested contours."""
        flood = mask.copy()
        flood_mask = np.zeros((self.height + 2, self.width + 2), np.uint8)
        cv2.floodFill(flood, flood_mask, (0, 0), 255)
        holes = cv2.bitwise_not(flood)
        return cv2.bitwise_or(mask, holes)

    def _next_contour_id(self) -> int:
        self._contour_counter += 1
        return self._contour_counter

    def _geometry_metrics(self, contour: np.ndarray) -> Dict[str, float]:
        area = float(cv2.contourArea(contour))
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = float(w / h) if h else float("inf")
        hull = cv2.convexHull(contour)
        hull_area = float(cv2.contourArea(hull))
        solidity = float(area / hull_area) if hull_area > 0 else 0.0
        return {
            "area": area,
            "relative_area": area / self.total_area if self.total_area else 0.0,
            "aspect_ratio": aspect_ratio,
            "solidity": solidity,
            "bbox": [int(x), int(y), int(w), int(h)],
        }

    def _record_debug(self, contour_id: int, status: str, reason: str, metrics: Dict) -> None:
        if not self.debug:
            return
        self.debug_log.append(
            {
                "contour_id": contour_id,
                "status": status,
                "reason": reason,
                "metrics": metrics,
            }
        )

    def _passes_geometry_filters(
        self,
        contour: np.ndarray,
        min_area: int,
        contour_id: int,
    ) -> Tuple[bool, Dict[str, float], str]:
        metrics = self._geometry_metrics(contour)
        min_area_px = max(float(min_area), self.total_area * self.min_area_ratio)

        if metrics["area"] < min_area_px:
            return False, metrics, f"area_below_minimum:{metrics['area']:.1f}<{min_area_px:.1f}"

        ratio = metrics["aspect_ratio"]
        min_ratio = 1.0 / self.max_aspect_ratio
        if ratio > self.max_aspect_ratio or ratio < min_ratio:
            return False, metrics, f"aspect_ratio_out_of_range:{ratio:.3f}"

        if metrics["solidity"] < 0.4:
            return False, metrics, f"low_solidity:{metrics['solidity']:.3f}"

        x, y, w, h = metrics["bbox"]
        touches_border = x <= 1 or y <= 1 or x + w >= self.width - 1 or y + h >= self.height - 1
        if touches_border and metrics["area"] > self.total_area * 0.65:
            return False, metrics, "large_background_touching_image_border"

        return True, metrics, "accepted"

    def _process_contour(
        self,
        contour: np.ndarray,
        min_area: int,
        allow_low_saturation: bool = False,
    ) -> Optional[ExtractedRegion]:
        """Validate a contour and convert it to an ``ExtractedRegion``."""
        contour_id = self._next_contour_id()
        accepted, metrics, reason = self._passes_geometry_filters(contour, min_area, contour_id)
        if not accepted:
            self._record_debug(contour_id, "REJECTED", reason, metrics)
            return None

        x, y, w, h = metrics["bbox"]
        mask_single = np.zeros((self.height, self.width), dtype=np.uint8)
        cv2.drawContours(mask_single, [contour], 0, 255, -1)
        mean_color = cv2.mean(self.image, mask=mask_single)[:3]
        b, g, r = mean_color

        if min(r, g, b) > 235 or max(r, g, b) < 25:
            self._record_debug(contour_id, "REJECTED", "near_white_or_black_region", metrics)
            return None

        if not allow_low_saturation and abs(r - g) < 10 and abs(g - b) < 10 and abs(r - b) < 10:
            if r > 200 or r < 50:
                self._record_debug(contour_id, "REJECTED", "low_saturation_gray_region", metrics)
                return None

        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.002 * perimeter, True)
        if len(approx) < 4:
            approx = contour

        moments = cv2.moments(contour)
        if moments["m00"] <= 0:
            self._record_debug(contour_id, "REJECTED", "zero_moment", metrics)
            return None

        self._record_debug(contour_id, "ACCEPTED", "accepted", metrics)
        return ExtractedRegion(
            contour=approx,
            centroid=(float(moments["m10"] / moments["m00"]), float(moments["m01"] / moments["m00"])),
            area=float(metrics["area"]),
            bbox=(int(x), int(y), int(w), int(h)),
            color=(int(b), int(g), int(r)),
        )

    def _remove_overlapping(
        self,
        regions: List[ExtractedRegion],
        overlap_threshold: float = 0.7,
    ) -> List[ExtractedRegion]:
        """Remove approximate duplicate detections using bounding-box IoU."""
        if len(regions) <= 1:
            return regions

        keep = []
        for region in sorted(regions, key=lambda item: item.area, reverse=True):
            duplicate = False
            for kept in keep:
                x1, y1, w1, h1 = region.bbox
                x2, y2, w2, h2 = kept.bbox
                xi, yi = max(x1, x2), max(y1, y2)
                wi = min(x1 + w1, x2 + w2) - xi
                hi = min(y1 + h1, y2 + h2) - yi
                if wi <= 0 or hi <= 0:
                    continue
                inter_area = wi * hi
                union_area = w1 * h1 + w2 * h2 - inter_area
                if union_area and inter_area / union_area > overlap_threshold:
                    duplicate = True
                    break
            if not duplicate:
                keep.append(region)
        return keep

    def segment_at_point(self, x: int, y: int, tolerance: int = 25) -> Optional[ExtractedRegion]:
        """Segment a connected region around a clicked point."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return None

        target_color = self.image[y, x].astype(np.float32)
        lab_image = cv2.cvtColor(self.image, cv2.COLOR_BGR2LAB).astype(np.float32)
        target_lab = cv2.cvtColor(np.uint8([[target_color]]), cv2.COLOR_BGR2LAB).astype(np.float32)[0, 0]
        diff = np.sqrt(np.sum((lab_image - target_lab) ** 2, axis=2))
        mask = (diff < tolerance).astype(np.uint8) * 255

        flood_mask = np.zeros((self.height + 2, self.width + 2), np.uint8)
        cv2.floodFill(mask, flood_mask, (x, y), 255, 0, 0, cv2.FLOODFILL_MASK_ONLY)
        region_mask = flood_mask[1:-1, 1:-1]
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        region_mask = cv2.morphologyEx(region_mask, cv2.MORPH_CLOSE, kernel)
        region_mask = self._fill_mask_holes(region_mask)

        contours, _ = cv2.findContours(region_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        containing = [
            contour for contour in contours if cv2.pointPolygonTest(contour, (x, y), False) >= 0
        ]
        contour = max(containing or contours, key=cv2.contourArea)
        return self._process_contour(contour, max(100, int(self.total_area * self.min_area_ratio)), True)

    def visualize(self, regions: Optional[List[ExtractedRegion]] = None) -> np.ndarray:
        """Render extracted regions as a colored overlay."""
        regions = self.regions if regions is None else regions
        overlay = self.image.copy()
        np.random.seed(42)
        colors = [
            (
                int(np.random.randint(100, 255)),
                int(np.random.randint(100, 255)),
                int(np.random.randint(100, 255)),
            )
            for _ in range(max(len(regions), 1))
        ]

        for i, region in enumerate(regions):
            color = colors[i % len(colors)]
            cv2.drawContours(overlay, [region.contour], -1, color, -1)
            cv2.drawContours(overlay, [region.contour], -1, (255, 255, 255), 2)
            cx, cy = int(region.centroid[0]), int(region.centroid[1])
            cv2.circle(overlay, (cx, cy), 5, (0, 0, 0), -1)
            cv2.putText(
                overlay,
                region.name or f"R{i + 1}",
                (cx + 6, cy - 6),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
            )
        return cv2.addWeighted(self.image, 0.4, overlay, 0.6, 0)

    def get_debug_report(self) -> List[Dict]:
        """Return contour-level segmentation decisions collected in debug mode."""
        return list(self.debug_log)


class MapSegmenter(AdvancedSegmenter):
    """Backward-compatible name used by the current modular webapp."""

