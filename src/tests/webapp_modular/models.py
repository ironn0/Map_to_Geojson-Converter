"""
📦 Data Models Module
Modelli Pydantic e dataclasses per la validazione dei dati

Author: Map to GeoJSON Converter Project
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
import numpy as np


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


class SegmentRequest(BaseModel):
    """Richiesta di segmentazione"""
    session_id: str
    n_colors: int = 40
    min_area: int = 500


class PointRequest(BaseModel):
    """Richiesta segmentazione da punto"""
    session_id: str
    x: int
    y: int


class ExportRequest(BaseModel):
    """Richiesta di esportazione GeoJSON"""
    session_id: str
    bounds: GeoBounds
    region_names: Optional[Dict[int, str]] = None


class UpdateRegionRequest(BaseModel):
    """Richiesta di aggiornamento regione"""
    session_id: str
    region_id: int
    points: List[List[float]]


class AlignRequest(BaseModel):
    """Richiesta di allineamento ai confini"""
    session_id: str
    bounds: GeoBounds
    reference_geojson: Optional[Dict] = None
    snap_strength: float = 0.5


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


class RegionDict(BaseModel):
    """Dizionario regione per JSON"""
    id: int
    name: str
    area: float
    centroid: List[float]
    bbox: List[int]
    color: str
    points: List[List[float]]
