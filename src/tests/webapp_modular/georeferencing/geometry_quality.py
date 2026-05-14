"""
🧹 Geometry quality post-processing
Validazione e sanitizzazione geometrie GeoJSON prima dell'export.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid


def _close_ring(coords: List[List[float]]) -> List[List[float]]:
    if not coords:
        return coords
    if coords[0] != coords[-1]:
        return coords + [coords[0]]
    return coords


def _sanitize_ring(coords: List[List[float]]) -> List[List[float]]:
    ring: List[List[float]] = []
    prev = None
    for x, y in coords:
        point = [float(x), float(y)]
        if point != prev:
            ring.append(point)
            prev = point
    return _close_ring(ring)


def _to_polygons(geometry: BaseGeometry) -> List[Polygon]:
    if geometry.is_empty:
        return []
    if isinstance(geometry, Polygon):
        return [geometry]
    if isinstance(geometry, MultiPolygon):
        return list(geometry.geoms)
    if hasattr(geometry, "geoms"):
        polygons: List[Polygon] = []
        for geom in geometry.geoms:
            polygons.extend(_to_polygons(geom))
        return polygons
    return []


def sanitize_polygon_geometry(
    coords: List[List[float]],
    min_polygon_area: float = 0.0,
    simplify_tolerance: float = 0.0,
    keep_multipolygons: bool = True,
) -> Tuple[Dict, Dict]:
    """
    Sanitizza un anello esterno e restituisce una geometria GeoJSON valida.
    """
    ring = _sanitize_ring(coords)
    if len(ring) < 4:
        raise ValueError("Geometria non valida: meno di 3 vertici unici")

    polygon = Polygon(ring)
    if not polygon.is_valid:
        try:
            polygon = make_valid(polygon)
        except Exception:
            polygon = polygon.buffer(0)

    polygons = _to_polygons(polygon)
    if min_polygon_area > 0:
        polygons = [poly for poly in polygons if poly.area >= min_polygon_area]
    if not polygons:
        raise ValueError("Geometria vuota dopo la sanitizzazione")

    processed: List[Polygon] = []
    for poly in polygons:
        clean_poly: BaseGeometry = poly
        if simplify_tolerance > 0:
            clean_poly = clean_poly.simplify(simplify_tolerance, preserve_topology=True)
        if not clean_poly.is_valid:
            clean_poly = clean_poly.buffer(0)
        processed.extend(_to_polygons(clean_poly))

    if not processed:
        raise ValueError("Geometria vuota dopo la semplificazione")

    if len(processed) == 1 or not keep_multipolygons:
        largest = max(processed, key=lambda p: p.area)
        out_ring = [[round(x, 6), round(y, 6)] for x, y in largest.exterior.coords]
        geometry = {"type": "Polygon", "coordinates": [out_ring]}
    else:
        multipoly_coords = []
        for poly in processed:
            ring_coords = [[round(x, 6), round(y, 6)] for x, y in poly.exterior.coords]
            multipoly_coords.append([ring_coords])
        geometry = {"type": "MultiPolygon", "coordinates": multipoly_coords}

    metadata = {
        "valid_input": Polygon(ring).is_valid,
        "parts": len(processed),
        "simplified": bool(simplify_tolerance > 0),
        "removed_small_parts": max(0, len(polygons) - len(processed)),
    }
    return geometry, metadata
