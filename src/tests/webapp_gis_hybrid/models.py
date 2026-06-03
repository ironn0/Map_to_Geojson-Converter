"""Shared data models for the GIS hybrid prototype."""

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np


@dataclass
class ExtractedRegion:
    """A raster region extracted from a map image."""

    contour: np.ndarray
    centroid: Tuple[float, float]
    area: float
    bbox: Tuple[int, int, int, int]
    color: Tuple[int, int, int]
    name: Optional[str] = None
    score: float = 0.0

