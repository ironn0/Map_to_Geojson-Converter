"""Affine georeferencing based on bounds or Ground Control Points."""

from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np


class Georeferencer:
    """Convert between image pixels and WGS84 coordinates using an affine matrix."""

    def __init__(self, width: int, height: int, bounds: Dict):
        self.width = width
        self.height = height
        self.north = bounds.get("north", 90)
        self.south = bounds.get("south", -90)
        self.east = bounds.get("east", 180)
        self.west = bounds.get("west", -180)
        self.lon_per_pixel = (self.east - self.west) / self.width
        self.lat_per_pixel = (self.north - self.south) / self.height
        self.affine_matrix = np.array(
            [
                [self.lon_per_pixel, 0.0, self.west],
                [0.0, -self.lat_per_pixel, self.north],
            ],
            dtype=float,
        )
        self.residuals: np.ndarray = np.array([])

    def estimate_transform_from_gcp(
        self,
        gcp_pixel: Sequence[Tuple[float, float]],
        gcp_geo: Sequence[Tuple[float, float]],
    ) -> np.ndarray:
        """Estimate a pixel-to-geo affine matrix from at least three GCP pairs.

        Args:
            gcp_pixel: Pixel coordinates as ``[(x, y), ...]``.
            gcp_geo: Geographic WGS84 coordinates as ``[(lon, lat), ...]``.

        Returns:
            A 2x3 affine matrix mapping ``[x, y, 1]`` to ``[lon, lat]``.
        """
        if len(gcp_pixel) != len(gcp_geo):
            raise ValueError("gcp_pixel and gcp_geo must contain the same number of points")
        if len(gcp_pixel) < 3:
            raise ValueError("at least three Ground Control Points are required")

        design = np.array([[float(x), float(y), 1.0] for x, y in gcp_pixel], dtype=float)
        target = np.array([[float(lon), float(lat)] for lon, lat in gcp_geo], dtype=float)
        coeffs, residuals, _, _ = np.linalg.lstsq(design, target, rcond=None)
        self.affine_matrix = coeffs.T
        predicted = design @ coeffs
        self.residuals = np.sqrt(np.sum((predicted - target) ** 2, axis=1))
        return self.affine_matrix.copy()

    def pixel_to_coord(self, x: float, y: float) -> Tuple[float, float]:
        """Convert a single pixel point to ``(lon, lat)``."""
        lon, lat = self.affine_matrix @ np.array([float(x), float(y), 1.0])
        return (round(float(lon), 6), round(float(lat), 6))

    def coord_to_pixel(self, lon: float, lat: float) -> Tuple[int, int]:
        """Convert ``(lon, lat)`` back to pixel coordinates using the affine inverse."""
        matrix_3x3 = np.vstack([self.affine_matrix, [0.0, 0.0, 1.0]])
        inverse = np.linalg.inv(matrix_3x3)
        x, y, _ = inverse @ np.array([float(lon), float(lat), 1.0])
        return (int(round(float(x))), int(round(float(y))))

    def pixel_to_geo(self, contour: np.ndarray | Iterable[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Convert an OpenCV contour or point iterable to geographic tuples."""
        points = contour.reshape(-1, 2) if hasattr(contour, "reshape") else contour
        return [self.pixel_to_coord(float(x), float(y)) for x, y in points]

    def contour_to_coords(self, contour: np.ndarray) -> List[List[float]]:
        """Convert an OpenCV contour to a closed GeoJSON coordinate ring."""
        coords = [list(point) for point in self.pixel_to_geo(contour)]
        if coords and coords[0] != coords[-1]:
            coords.append(coords[0])
        return coords

    def coords_to_pixels(self, coords: List[List[float]]) -> List[List[int]]:
        """Convert GeoJSON-style coordinate pairs back to pixel pairs."""
        return [list(self.coord_to_pixel(lon, lat)) for lon, lat in coords]

    def get_bounds_dict(self) -> Dict:
        """Return the nominal geographic bounds used for the initial transform."""
        return {
            "north": self.north,
            "south": self.south,
            "east": self.east,
            "west": self.west,
        }

    def get_transform_report(self) -> Dict:
        """Return the active affine transform and GCP residuals."""
        return {
            "affine_matrix": self.affine_matrix.tolist(),
            "residuals": self.residuals.tolist(),
            "mean_residual": float(np.mean(self.residuals)) if self.residuals.size else 0.0,
        }

