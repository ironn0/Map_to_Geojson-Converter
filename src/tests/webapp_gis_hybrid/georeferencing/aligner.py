"""Topological snap-to-reference alignment using Shapely and GeoPandas."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

try:
    import geopandas as gpd
    from shapely.geometry import MultiPolygon, Polygon, mapping, shape
    from shapely.validation import make_valid
except ImportError as exc:  # pragma: no cover - exercised only on missing deps
    gpd = None
    Polygon = None
    MultiPolygon = None
    mapping = None
    shape = None
    make_valid = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


def _require_gis() -> None:
    if _IMPORT_ERROR is not None:
        raise ImportError("geopandas and shapely are required for GIS alignment") from _IMPORT_ERROR


def _valid_geometry(geometry):
    """Return a valid Shapely geometry, repairing topology when possible."""
    _require_gis()
    if geometry is None or geometry.is_empty:
        return geometry
    if geometry.is_valid:
        return geometry
    repaired = make_valid(geometry)
    if repaired.geom_type == "GeometryCollection":
        polygons = [geom for geom in repaired.geoms if geom.geom_type in {"Polygon", "MultiPolygon"}]
        if not polygons:
            return repaired
        return max(polygons, key=lambda geom: geom.area)
    return repaired


def _geometry_iou(left, right) -> float:
    left = _valid_geometry(left)
    right = _valid_geometry(right)
    if left is None or right is None or left.is_empty or right.is_empty:
        return 0.0
    intersection = left.intersection(right).area
    union = left.union(right).area
    return float(intersection / union) if union else 0.0


def _feature_collection_to_gdf(reference_geojson: Dict):
    _require_gis()
    if not reference_geojson:
        return gpd.GeoDataFrame(geometry=[])
    if reference_geojson.get("type") == "FeatureCollection":
        return gpd.GeoDataFrame.from_features(reference_geojson.get("features", []), crs="EPSG:4326")
    if reference_geojson.get("type") == "Feature":
        return gpd.GeoDataFrame.from_features([reference_geojson], crs="EPSG:4326")
    return gpd.GeoDataFrame(geometry=[shape(reference_geojson)], crs="EPSG:4326")


def _coords_to_polygon(coords: List):
    _require_gis()
    ring = coords[0] if coords and isinstance(coords[0][0], list) else coords
    polygon = Polygon(ring)
    return _valid_geometry(polygon)


def _polygon_to_geojson_coords(geometry) -> List:
    """Return GeoJSON coordinates, choosing the largest polygon from multipolygons."""
    _require_gis()
    geometry = _valid_geometry(geometry)
    if geometry.geom_type == "MultiPolygon":
        geometry = max(geometry.geoms, key=lambda geom: geom.area)
    if geometry.geom_type != "Polygon":
        return []
    return [list(map(list, geometry.exterior.coords))]


def align_with_reference(extracted_polygon, reference_gdf, iou_threshold: float = 0.6):
    """Snap an extracted polygon to the best reference polygon when IoU is high.

    If the best Jaccard/IoU score is below ``iou_threshold``, the original
    polygon is returned after ``make_valid`` repair. When the score passes the
    threshold, the official reference geometry fully replaces the CV geometry.
    """
    _require_gis()
    polygon = _valid_geometry(extracted_polygon)
    if polygon is None or polygon.is_empty or reference_gdf is None or reference_gdf.empty:
        return polygon

    best_score = 0.0
    best_geometry = None
    for geometry in reference_gdf.geometry:
        candidate = _valid_geometry(geometry)
        score = _geometry_iou(polygon, candidate)
        if score > best_score:
            best_score = score
            best_geometry = candidate

    if best_geometry is not None and best_score >= iou_threshold:
        return _valid_geometry(best_geometry)
    return polygon


class TerritoryAligner:
    """Align extracted GeoJSON features to a reference boundary layer."""

    def __init__(self, reference_geojson: Dict = None, iou_threshold: float = 0.6):
        _require_gis()
        self.reference_gdf = gpd.GeoDataFrame(geometry=[])
        self.reference_features = []
        self.iou_threshold = iou_threshold
        if reference_geojson:
            self.load_reference(reference_geojson)

    def load_reference(self, geojson: Dict) -> None:
        """Load a Feature or FeatureCollection as the snap reference layer."""
        self.reference_gdf = _feature_collection_to_gdf(geojson)
        if geojson.get("type") == "FeatureCollection":
            self.reference_features = geojson.get("features", [])
        elif geojson.get("type") == "Feature":
            self.reference_features = [geojson]
        else:
            self.reference_features = [{"type": "Feature", "properties": {}, "geometry": geojson}]

    def find_best_match(self, region_coords: List, threshold: float = 0.3) -> Optional[Dict]:
        """Return the reference feature with the best polygon IoU score."""
        if self.reference_gdf.empty:
            return None

        polygon = _coords_to_polygon(region_coords)
        best_idx = None
        best_score = 0.0
        for idx, geometry in enumerate(self.reference_gdf.geometry):
            score = _geometry_iou(polygon, geometry)
            if score > best_score:
                best_idx = idx
                best_score = score

        if best_idx is None or best_score < threshold:
            return None

        feature = self.reference_features[best_idx] if best_idx < len(self.reference_features) else None
        return {
            "feature": feature,
            "score": best_score,
            "geometry": self.reference_gdf.geometry.iloc[best_idx],
        }

    def align_region(self, region_coords: List, snap_strength: float = 0.5) -> List:
        """Snap one region to the reference layer, preserving old method signature."""
        if snap_strength <= 0 or self.reference_gdf.empty:
            return region_coords

        polygon = _coords_to_polygon(region_coords)
        threshold = max(0.05, min(0.95, self.iou_threshold / max(snap_strength, 0.01)))
        aligned = align_with_reference(polygon, self.reference_gdf, threshold)
        coords = _polygon_to_geojson_coords(aligned)
        return coords if coords else region_coords

    def align_all(self, features: List[Dict], snap_strength: float = 0.5) -> List[Dict]:
        """Align all polygon features against the reference boundary layer."""
        aligned_features = []
        for feature in features:
            geometry = feature.get("geometry", {})
            if geometry.get("type") != "Polygon":
                aligned_features.append(feature)
                continue

            coords = geometry.get("coordinates", [[]])
            aligned_coords = self.align_region(coords, snap_strength)
            aligned_geometry = {"type": "Polygon", "coordinates": aligned_coords}

            aligned_feature = dict(feature)
            aligned_feature["properties"] = dict(feature.get("properties", {}))
            aligned_feature["geometry"] = aligned_geometry
            match = self.find_best_match(coords, threshold=0.0)
            if match:
                aligned_feature["properties"]["alignment_iou"] = round(float(match["score"]), 6)
            aligned_features.append(aligned_feature)
        return aligned_features

    def geometry_to_feature(self, geometry, properties: Optional[Dict] = None) -> Dict:
        """Create a GeoJSON feature from a Shapely geometry."""
        return {
            "type": "Feature",
            "properties": properties or {},
            "geometry": mapping(_valid_geometry(geometry)),
        }

