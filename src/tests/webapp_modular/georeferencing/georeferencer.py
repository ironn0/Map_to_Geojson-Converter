"""
🌍 Georeferencer Module
Converte coordinate pixel in coordinate geografiche

Author: Map to GeoJSON Converter Project
"""

import math
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from .cv_registration import build_cv_auto_transform


class Georeferencer:
    """Converte coordinate pixel in coordinate geografiche."""

    def __init__(
        self,
        width: int,
        height: int,
        bounds: Dict,
        georeferencing: Optional[Dict[str, Any]] = None,
        source_image: Optional[np.ndarray] = None,
    ):
        if width <= 0 or height <= 0:
            raise ValueError("Dimensioni immagine non valide per la georeferenziazione")

        self.width = width
        self.height = height
        self.north = bounds.get("north", 90)
        self.south = bounds.get("south", -90)
        self.east = bounds.get("east", 180)
        self.west = bounds.get("west", -180)
        if self.north <= self.south or self.east <= self.west:
            raise ValueError("Confini geografici non validi")

        self.lon_per_pixel = (self.east - self.west) / self.width
        self.lat_per_pixel = (self.north - self.south) / self.height
        self.transform_mode = "bounds"
        self._transform = None
        self._inverse_transform = None
        self.transform_metrics = {
            "mode": "bounds",
            "num_gcps": 0,
            "rmse_degrees": 0.0,
            "rmse_meters": 0.0,
            "rmse_ratio": 0.0,
            "validated": True,
        }
        self.source_image = source_image

        georef = georeferencing or {}
        self._init_advanced_transform(georef)
        projection_warning = self._projection_warning()
        if projection_warning:
            self.transform_metrics["projection_warning"] = projection_warning

    def _init_advanced_transform(self, georeferencing: Dict[str, Any]) -> None:
        mode = georeferencing.get("mode", "bounds")
        gcps = georeferencing.get("gcps", []) or []
        validate_quality = georeferencing.get("validate_quality", True)
        max_rmse_ratio = georeferencing.get("max_rmse_ratio", 0.08)

        if mode == "bounds" or not gcps:
            if mode != "cv_auto":
                return

        if mode == "cv_auto":
            allow_fallback = bool(georeferencing.get("allow_fallback", True))
            try:
                cv_transform, cv_metrics = build_cv_auto_transform(self.source_image, georeferencing)
            except ValueError as err:
                if allow_fallback:
                    self.transform_metrics = {
                        **self.transform_metrics,
                        "mode": "bounds",
                        "validated": False,
                        "fallback_from": "cv_auto",
                        "fallback_reason": f"cv_registration_failed:{str(err)}",
                    }
                    return
                raise

            confidence_threshold = float(georeferencing.get("confidence_threshold", 0.35))
            confidence = float(cv_metrics["cv_confidence"])

            if confidence < confidence_threshold:
                if allow_fallback:
                    self.transform_metrics = {
                        **self.transform_metrics,
                        "mode": "bounds",
                        "validated": False,
                        "fallback_from": "cv_auto",
                        "fallback_reason": "low_confidence",
                        "cv_confidence": round(confidence, 6),
                        "cv_confidence_threshold": round(confidence_threshold, 6),
                    }
                    return
                raise ValueError(
                    "cv_auto rifiutato: confidence troppo bassa "
                    f"({confidence:.4f} < {confidence_threshold:.4f})"
                )

            self._transform = cv_transform
            self._inverse_transform = np.linalg.inv(cv_transform)
            self.transform_mode = "cv_auto"
            self.transform_metrics = cv_metrics
            return

        points_px = np.array(
            [[float(g["pixel_x"]), float(g["pixel_y"])] for g in gcps], dtype=np.float64
        )
        points_geo = np.array(
            [[float(g["lon"]), float(g["lat"])] for g in gcps], dtype=np.float64
        )

        if mode == "auto":
            mode = "homography" if len(gcps) >= 4 else "affine"

        if mode == "affine":
            if len(gcps) < 3:
                raise ValueError("Servono almeno 3 GCP per affine")
            transform, _ = cv2.estimateAffine2D(points_px, points_geo)
            if transform is None:
                raise ValueError("Impossibile stimare trasformazione affine dai GCP")
            affine_3x3 = np.vstack([transform, np.array([0.0, 0.0, 1.0])])
            self._transform = affine_3x3
            self._inverse_transform = np.linalg.inv(affine_3x3)
            self.transform_mode = "affine"
        elif mode == "homography":
            if len(gcps) < 4:
                raise ValueError("Servono almeno 4 GCP per homography")
            transform, _ = cv2.findHomography(points_px, points_geo, method=cv2.RANSAC)
            if transform is None:
                raise ValueError("Impossibile stimare omografia dai GCP")
            self._transform = transform
            self._inverse_transform = np.linalg.inv(transform)
            self.transform_mode = "homography"
        else:
            raise ValueError(f"Modalita georeferencing non supportata: {mode}")

        residuals = [
            self._coord_error(self._pixel_to_coord_transformed(px, py), (lon, lat))
            for (px, py), (lon, lat) in zip(points_px, points_geo)
        ]
        rmse_deg = math.sqrt(sum(err[0] ** 2 for err in residuals) / len(residuals))
        rmse_m = math.sqrt(sum(err[1] ** 2 for err in residuals) / len(residuals))
        diagonal_deg = math.sqrt((self.east - self.west) ** 2 + (self.north - self.south) ** 2)
        rmse_ratio = rmse_deg / diagonal_deg if diagonal_deg > 0 else 0.0

        if validate_quality and rmse_ratio > float(max_rmse_ratio):
            raise ValueError(
                "Trasformazione GCP rifiutata: errore residuo troppo elevato "
                f"(ratio={rmse_ratio:.4f}, max={max_rmse_ratio:.4f})"
            )

        self.transform_metrics = {
            "mode": self.transform_mode,
            "num_gcps": len(gcps),
            "rmse_degrees": round(rmse_deg, 8),
            "rmse_meters": round(rmse_m, 3),
            "rmse_ratio": round(rmse_ratio, 6),
            "validated": bool(validate_quality),
        }

    def _coord_error(
        self, predicted: Tuple[float, float], target: Tuple[float, float]
    ) -> Tuple[float, float]:
        dlon = predicted[0] - target[0]
        dlat = predicted[1] - target[1]
        error_deg = math.sqrt(dlon**2 + dlat**2)
        mean_lat = math.radians((predicted[1] + target[1]) / 2.0)
        m_per_deg_lat = 111_320.0
        m_per_deg_lon = 111_320.0 * math.cos(mean_lat)
        error_m = math.sqrt((dlon * m_per_deg_lon) ** 2 + (dlat * m_per_deg_lat) ** 2)
        return error_deg, error_m

    def _pixel_to_coord_transformed(self, x: float, y: float) -> Tuple[float, float]:
        if self._transform is None:
            lon = self.west + (x * self.lon_per_pixel)
            lat = self.north - (y * self.lat_per_pixel)
            return lon, lat

        point = np.array([x, y, 1.0], dtype=np.float64)
        projected = self._transform @ point
        if abs(projected[2]) < 1e-12:
            raise ValueError("Trasformazione non invertibile sul punto richiesto")
        lon = projected[0] / projected[2]
        lat = projected[1] / projected[2]
        return lon, lat

    def _coord_to_pixel_transformed(self, lon: float, lat: float) -> Tuple[float, float]:
        if self._inverse_transform is None:
            x = (lon - self.west) / self.lon_per_pixel
            y = (self.north - lat) / self.lat_per_pixel
            return x, y

        point = np.array([lon, lat, 1.0], dtype=np.float64)
        projected = self._inverse_transform @ point
        if abs(projected[2]) < 1e-12:
            raise ValueError("Trasformazione inversa non disponibile per il punto")
        x = projected[0] / projected[2]
        y = projected[1] / projected[2]
        return x, y

    def _projection_warning(self) -> Optional[str]:
        lat_span = self.north - self.south
        if self.north > 75 or self.south < -75:
            return (
                "Bounds vicini ai poli: la conversione lineare lat/lon puo introdurre distorsioni. "
                "Usa GCP o cv_auto per risultati migliori."
            )
        if lat_span > 120:
            return (
                "Bounds molto estesi in latitudine: una mappa piana su planisfero puo deformare aree e scale. "
                "Verifica il risultato con riferimenti reali."
            )
        return None

    def pixel_to_coord(self, x: int, y: int) -> Tuple[float, float]:
        """Converte coordinate pixel in longitudine/latitudine."""
        lon, lat = self._pixel_to_coord_transformed(float(x), float(y))
        return round(lon, 6), round(lat, 6)

    def coord_to_pixel(self, lon: float, lat: float) -> Tuple[int, int]:
        """Converte coordinate geografiche in pixel."""
        x, y = self._coord_to_pixel_transformed(float(lon), float(lat))
        return int(round(x)), int(round(y))

    def contour_to_coords(self, contour: np.ndarray) -> List[List[float]]:
        """Converte un contorno di pixel in coordinate geografiche."""
        if contour is None or contour.size == 0:
            raise ValueError("Contorno vuoto o non valido")

        points = contour.reshape(-1, 2) if len(contour.shape) == 3 else contour
        if len(points) < 3:
            raise ValueError("Un poligono richiede almeno 3 punti")

        coords = [list(self.pixel_to_coord(int(x), int(y))) for x, y in points]
        if coords and coords[0] != coords[-1]:
            coords.append(coords[0])
        return coords

    def coords_to_pixels(self, coords: List[List[float]]) -> List[List[int]]:
        """Converte coordinate geografiche in pixel."""
        return [list(self.coord_to_pixel(lon, lat)) for lon, lat in coords]

    def get_bounds_dict(self) -> Dict:
        """Restituisce i confini come dizionario."""
        return {
            "north": self.north,
            "south": self.south,
            "east": self.east,
            "west": self.west,
        }

    def get_transform_metrics(self) -> Dict[str, Any]:
        """Restituisce metriche di qualita della georeferenziazione."""
        return dict(self.transform_metrics)
