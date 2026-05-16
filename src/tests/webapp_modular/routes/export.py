"""
📦 Export Routes
Endpoint per l'esportazione GeoJSON

Author: Map to GeoJSON Converter Project
"""

from config import GEO_PRESETS, GEOMETRY_SANITIZE_DEFAULTS
from fastapi import APIRouter, HTTPException
from georeferencing import Georeferencer, sanitize_polygon_geometry
from models import ExportRequest
from session_manager import get_session
from utils import validate_bounds, validate_contour

router = APIRouter(prefix="/api", tags=["export"])


@router.post("/export")
async def export_geojson(req: ExportRequest):
    """Esporta le regioni in formato GeoJSON"""
    
    session = get_session(req.session_id)
    if session is None:
        raise HTTPException(404, "Sessione non trovata")

    regions = session["regions"]

    has_circle = bool(req.include_detected_circle and session.get("detected_circle"))
    if not regions and not has_circle:
        raise HTTPException(400, "Nessuna regione da esportare")

    bounds_dict = req.bounds.model_dump()
    if not validate_bounds(bounds_dict):
        raise HTTPException(400, "Confini geografici non validi")
    
    georeferencing_cfg = req.georeferencing.model_dump() if req.georeferencing else None

    try:
        georef = Georeferencer(
            session["width"],
            session["height"],
            bounds_dict,
            georeferencing=georeferencing_cfg,
            source_image=session.get("image"),
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    sanitize_cfg = dict(GEOMETRY_SANITIZE_DEFAULTS)
    if req.geometry_sanitize:
        sanitize_cfg.update(req.geometry_sanitize.model_dump())

    features = []
    for i, region in enumerate(regions):
        if not validate_contour(region.contour):
            raise HTTPException(400, f"Contorno non valido per la regione {i}")

        try:
            coords = georef.contour_to_coords(region.contour)
        except ValueError as e:
            raise HTTPException(400, f"Errore geometria regione {i}: {str(e)}")
        
        name = region.name or f"Regione {i + 1}"
        if req.region_names and i in req.region_names:
            name = req.region_names[i]
        
        geometry = {
            "type": "Polygon",
            "coordinates": [coords],
        }
        quality_meta = {"sanitized": False}
        if sanitize_cfg["enabled"]:
            try:
                geometry, quality_meta = sanitize_polygon_geometry(
                    coords,
                    min_polygon_area=float(sanitize_cfg["min_polygon_area"]),
                    simplify_tolerance=float(sanitize_cfg["simplify_tolerance"]),
                    keep_multipolygons=bool(sanitize_cfg["keep_multipolygons"]),
                )
            except ValueError as e:
                raise HTTPException(400, f"Errore sanitizzazione regione {i}: {str(e)}")
            quality_meta["sanitized"] = True

        features.append({
            "type": "Feature",
            "properties": {
                "id": i,
                "name": name,
                "area_pixels": region.area,
                "color": f"#{region.color[2]:02x}{region.color[1]:02x}{region.color[0]:02x}",
                "geometry_quality": quality_meta,
            },
            "geometry": geometry,
        })

    if req.include_detected_circle and session.get("detected_circle"):
        circle = session["detected_circle"]
        circle_props = {
            "type": "detected-circle",
            "circle": {
                "center": circle.get("geo_center"),
                "radius_m": circle.get("radius_m"),
                "radius_std_m": circle.get("radius_std_m"),
                "accuracy_level": circle.get("accuracy_level"),
                "estimated_center_error_m": circle.get("estimated_center_error_m"),
                "confidence": circle.get("confidence"),
                "quality_metrics": circle.get("quality_metrics", {}),
            },
        }
        features.append(
            {
                "type": "Feature",
                "properties": circle_props,
                "geometry": circle.get("geojson_geometry"),
            }
        )

    response_payload = {
        "type": "FeatureCollection",
        "properties": {
            "source": "Map to GeoJSON Converter",
            "bounds": bounds_dict,
            "georeferencing": georef.get_transform_metrics(),
            "geometry_sanitize": sanitize_cfg,
            "detected_circle_included": bool(
                req.include_detected_circle and session.get("detected_circle")
            ),
        },
        "features": features,
    }
    return response_payload


@router.get("/presets")
async def get_presets():
    """Restituisce i preset geografici disponibili"""
    return GEO_PRESETS
