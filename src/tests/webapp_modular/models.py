"""
📦 Data Models Module
Modelli Pydantic e dataclasses per la validazione dei dati

Author: Map to GeoJSON Converter Project
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Tuple

import numpy as np
from pydantic import BaseModel, Field, model_validator

# ==================== Dataclasses ====================

@dataclass
class ExtractedRegion:
    """Regione estratta dalla mappa"""
    contour: np.ndarray
    centroid: Tuple[float, float]
    area: float
    bbox: Tuple[int, int, int, int]
    color: Tuple[int, int, int]
    name: Optional[str] = None


# ==================== Pydantic Models ====================

class GeoBounds(BaseModel):
    """Coordinate geografiche dei confini"""
    north: float = 47.1
    south: float = 35.5
    east: float = 18.5
    west: float = 6.6

    @model_validator(mode="after")
    def validate_bounds(self):
        values = [self.north, self.south, self.east, self.west]
        if not all(math.isfinite(v) for v in values):
            raise ValueError("I confini geografici devono essere numeri finiti")

        if self.north <= self.south:
            raise ValueError("north deve essere maggiore di south")
        if self.east <= self.west:
            raise ValueError("east deve essere maggiore di west")

        if not (-90 <= self.south <= 90 and -90 <= self.north <= 90):
            raise ValueError("Le latitudini devono essere comprese tra -90 e 90")
        if not (-180 <= self.west <= 180 and -180 <= self.east <= 180):
            raise ValueError("Le longitudini devono essere comprese tra -180 e 180")

        return self


class SegmentRequest(BaseModel):
    """Richiesta di segmentazione"""
    session_id: str
    n_colors: int = 40
    min_area: int = 500
    robust_mode: bool = False
    robust_settings: Optional["SegmentationRobustSettings"] = None


class PointRequest(BaseModel):
    """Richiesta segmentazione da punto"""
    session_id: str
    x: int = Field(ge=0)
    y: int = Field(ge=0)


class ExportRequest(BaseModel):
    """Richiesta di esportazione GeoJSON"""
    session_id: str
    bounds: GeoBounds
    region_names: Optional[Dict[int, str]] = None
    georeferencing: Optional["GeoreferencingRequest"] = None
    geometry_sanitize: Optional["GeometrySanitizeSettings"] = None
    include_detected_circle: bool = True


class UpdateRegionRequest(BaseModel):
    """Richiesta di aggiornamento regione"""
    session_id: str
    region_id: int
    points: List[List[float]]

    @model_validator(mode="after")
    def validate_points(self):
        if len(self.points) < 3:
            raise ValueError("Servono almeno 3 punti")
        for point in self.points:
            if len(point) != 2:
                raise ValueError("Ogni punto deve avere due coordinate [x, y]")
            if not all(math.isfinite(v) for v in point):
                raise ValueError("I punti devono essere finiti")
        return self


class AddRegionRequest(BaseModel):
    """Richiesta di creazione nuova regione lato API."""

    session_id: str
    points: List[List[float]]
    name: Optional[str] = None
    color: Optional[str] = None

    @model_validator(mode="after")
    def validate_points(self):
        if len(self.points) < 3:
            raise ValueError("Servono almeno 3 punti")
        for point in self.points:
            if len(point) != 2:
                raise ValueError("Ogni punto deve avere due coordinate [x, y]")
            if not all(math.isfinite(v) for v in point):
                raise ValueError("I punti devono essere finiti")
        return self


class AlignRequest(BaseModel):
    """Richiesta di allineamento ai confini"""
    session_id: str
    bounds: GeoBounds
    reference_geojson: Optional[Dict] = None
    snap_strength: float = 0.5
    georeferencing: Optional["GeoreferencingRequest"] = None


class CircleDetectRequest(BaseModel):
    """Richiesta di rilevamento + georeferenziazione cerchio."""

    session_id: str
    bounds: GeoBounds
    georeferencing: Optional["GeoreferencingRequest"] = None
    strict_center_target_m: float = 5.0

    @model_validator(mode="after")
    def validate_strict_target(self):
        if self.strict_center_target_m <= 0:
            raise ValueError("strict_center_target_m deve essere > 0")
        return self


class GroundControlPoint(BaseModel):
    """Punto di controllo pixel -> coordinate geografiche."""

    pixel_x: float
    pixel_y: float
    lon: float
    lat: float

    @model_validator(mode="after")
    def validate_values(self):
        values = [self.pixel_x, self.pixel_y, self.lon, self.lat]
        if not all(math.isfinite(v) for v in values):
            raise ValueError("I GCP devono contenere valori finiti")
        if not (-180 <= self.lon <= 180):
            raise ValueError("La longitudine del GCP deve essere tra -180 e 180")
        if not (-90 <= self.lat <= 90):
            raise ValueError("La latitudine del GCP deve essere tra -90 e 90")
        return self


class GeoreferencingRequest(BaseModel):
    """Configurazione opzionale per georeferenziazione avanzata."""

    mode: Literal["bounds", "affine", "homography", "auto", "cv_auto"] = "bounds"
    gcps: List[GroundControlPoint] = Field(default_factory=list)
    validate_quality: bool = True
    max_rmse_ratio: float = 0.08
    allow_fallback: bool = True
    min_matches: int = 30
    inlier_threshold: float = 3.0
    confidence_threshold: float = 0.35
    cv_reference_image_base64: Optional[str] = None
    cv_reference_bounds: Optional[GeoBounds] = None

    @model_validator(mode="after")
    def validate_gcps(self):
        if self.mode == "affine" and len(self.gcps) < 3:
            raise ValueError("Servono almeno 3 GCP per affine")
        if self.mode == "homography" and len(self.gcps) < 4:
            raise ValueError("Servono almeno 4 GCP per homography")
        if self.mode == "auto" and self.gcps and len(self.gcps) < 3:
            raise ValueError("Servono almeno 3 GCP per usare la modalita auto")
        if self.mode == "cv_auto":
            if not self.cv_reference_image_base64:
                raise ValueError("cv_reference_image_base64 e obbligatoria per cv_auto")
            if not self.cv_reference_bounds:
                raise ValueError("cv_reference_bounds e obbligatorio per cv_auto")
            if self.min_matches < 8:
                raise ValueError("min_matches deve essere >= 8 per cv_auto")
            if self.inlier_threshold <= 0:
                raise ValueError("inlier_threshold deve essere > 0")
            if not (0 < self.confidence_threshold <= 1):
                raise ValueError("confidence_threshold deve essere tra 0 e 1")
        if self.max_rmse_ratio <= 0:
            raise ValueError("max_rmse_ratio deve essere > 0")
        return self


class GeometrySanitizeSettings(BaseModel):
    """Opzioni di validazione/sanitizzazione geometrica in export."""

    enabled: bool = False
    min_polygon_area: float = 0.0
    simplify_tolerance: float = 0.0
    keep_multipolygons: bool = True

    @model_validator(mode="after")
    def validate_thresholds(self):
        if self.min_polygon_area < 0:
            raise ValueError("min_polygon_area non puo essere negativo")
        if self.simplify_tolerance < 0:
            raise ValueError("simplify_tolerance non puo essere negativo")
        return self


class SegmentationRobustSettings(BaseModel):
    """Configurazione opt-in per mappe difficili."""

    denoise_strength: float = 10.0
    clahe_clip_limit: float = 2.5
    adaptive_block_size: int = 41
    adaptive_c: float = 2.0
    text_suppression: bool = True
    morphology_kernel: int = 5
    contour_min_points: int = 4
    contour_solidity_min: float = 0.3
    contour_smoothing_epsilon_scale: float = 0.002
    artifact_min_component_area: int = 0

    @model_validator(mode="after")
    def validate_settings(self):
        if self.denoise_strength < 0:
            raise ValueError("denoise_strength deve essere >= 0")
        if self.clahe_clip_limit <= 0:
            raise ValueError("clahe_clip_limit deve essere > 0")
        if self.adaptive_block_size < 3 or self.adaptive_block_size % 2 == 0:
            raise ValueError("adaptive_block_size deve essere dispari e >= 3")
        if self.morphology_kernel < 1:
            raise ValueError("morphology_kernel deve essere >= 1")
        if self.contour_min_points < 3:
            raise ValueError("contour_min_points deve essere >= 3")
        if not (0 <= self.contour_solidity_min <= 1):
            raise ValueError("contour_solidity_min deve essere tra 0 e 1")
        if self.contour_smoothing_epsilon_scale < 0:
            raise ValueError("contour_smoothing_epsilon_scale deve essere >= 0")
        if self.artifact_min_component_area < 0:
            raise ValueError("artifact_min_component_area deve essere >= 0")
        return self


# ==================== Response Models ====================

class UploadResponse(BaseModel):
    """Risposta upload immagine"""
    session_id: str
    filename: str
    width: int
    height: int
    image: str


class SegmentResponse(BaseModel):
    """Risposta segmentazione"""
    success: bool
    num_regions: int
    regions: List[Dict]
    visualization: str


class CircleDetectResponse(BaseModel):
    """Risposta rilevamento cerchio."""

    success: bool
    circle: Dict
    georeferencing: Dict


class RegionDict(BaseModel):
    """Dizionario regione per JSON"""
    id: int
    name: str
    area: float
    centroid: List[float]
    bbox: List[int]
    color: str
    points: List[List[float]]


SegmentRequest.model_rebuild()
ExportRequest.model_rebuild()
AlignRequest.model_rebuild()
