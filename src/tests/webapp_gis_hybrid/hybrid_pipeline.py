"""High-level orchestration for the GIS hybrid map digitizing flow."""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

try:
    from georeferencing import Georeferencer, TerritoryAligner
    from segmentation import AdvancedSegmenter
except ImportError:  # pragma: no cover - package import path
    from .georeferencing import Georeferencer, TerritoryAligner
    from .segmentation import AdvancedSegmenter


def regions_to_features(regions, georef: Georeferencer) -> List[Dict]:
    """Convert extracted pixel regions to GeoJSON polygon features."""
    features = []
    for idx, region in enumerate(regions):
        coords = georef.contour_to_coords(region.contour)
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "id": idx,
                    "name": region.name or f"Regione {idx + 1}",
                    "area_pixels": region.area,
                    "color": f"#{region.color[2]:02x}{region.color[1]:02x}{region.color[0]:02x}",
                    "segmentation_score": region.score,
                },
                "geometry": {"type": "Polygon", "coordinates": [coords]},
            }
        )
    return features


def run_hybrid_extraction(
    image: np.ndarray,
    bounds: Dict,
    reference_geojson: Optional[Dict] = None,
    gcp_pixel: Optional[Sequence[Tuple[float, float]]] = None,
    gcp_geo: Optional[Sequence[Tuple[float, float]]] = None,
    n_colors: int = 40,
    min_area: int = 500,
    debug: bool = False,
) -> Dict:
    """Run segmentation, georeferencing and optional snap-to-reference alignment."""
    height, width = image.shape[:2]
    segmenter = AdvancedSegmenter(image, debug=debug)
    regions = segmenter.segment(n_colors=n_colors, min_area=min_area)

    georef = Georeferencer(width, height, bounds)
    if gcp_pixel is not None or gcp_geo is not None:
        if gcp_pixel is None or gcp_geo is None:
            raise ValueError("gcp_pixel and gcp_geo must be provided together")
        georef.estimate_transform_from_gcp(gcp_pixel, gcp_geo)

    features = regions_to_features(regions, georef)
    aligned_features = features
    if reference_geojson:
        aligned_features = TerritoryAligner(reference_geojson).align_all(features, snap_strength=1.0)

    return {
        "type": "FeatureCollection",
        "properties": {
            "source": "webapp_gis_hybrid",
            "bounds": bounds,
            "image_size": {"width": width, "height": height},
            "transform": georef.get_transform_report(),
            "debug": segmenter.get_debug_report() if debug else [],
        },
        "features": aligned_features,
    }

