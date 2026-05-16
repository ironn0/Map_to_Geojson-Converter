"""
🌍 Georeferencing Package
Moduli per la georeferenziazione e allineamento territoriale

Author: Map to GeoJSON Converter Project
"""

from .aligner import TerritoryAligner
from .circle_detection import detect_and_georeference_circle
from .geometry_quality import sanitize_polygon_geometry
from .georeferencer import Georeferencer

__all__ = [
    "Georeferencer",
    "TerritoryAligner",
    "sanitize_polygon_geometry",
    "detect_and_georeference_circle",
]
