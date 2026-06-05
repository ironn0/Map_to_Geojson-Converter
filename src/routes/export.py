"""
📦 Export Routes
Endpoint per l'esportazione GeoJSON

Author: Map to GeoJSON Converter Project
"""

from fastapi import APIRouter, HTTPException
from typing import Optional

from models import ExportRequest
from georeferencing import Georeferencer
from config import GEO_PRESETS
from session_manager import sessions

router = APIRouter(prefix="/api", tags=["export"])


def _client_region_to_feature(region: dict, idx: int, georef: Georeferencer) -> Optional[dict]:
    """Converte una regione editata nel browser in una Feature GeoJSON."""
    points = region.get("points") or []
    if len(points) < 3:
        return None

    coords = [list(georef.pixel_to_coord(float(p[0]), float(p[1]))) for p in points]
    if coords and coords[0] != coords[-1]:
        coords.append(coords[0])

    custom_properties = region.get("properties") or {}
    if not isinstance(custom_properties, dict):
        custom_properties = {}

    return {
        "type": "Feature",
        "properties": {
            **custom_properties,
            "id": region.get("id", idx),
            "name": region.get("name") or f"Regione {idx + 1}",
            "type": region.get("type", "area"),
            "area_pixels": region.get("area"),
            "color": region.get("color", "#3b82f6"),
            "description": region.get("description", "")
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [coords]
        }
    }


def _client_point_to_feature(point: dict, idx: int, georef: Georeferencer) -> dict:
    """Converte un punto di interesse editato nel browser in GeoJSON."""
    lon, lat = georef.pixel_to_coord(float(point.get("x", 0)), float(point.get("y", 0)))
    custom_properties = point.get("properties") or {}
    if not isinstance(custom_properties, dict):
        custom_properties = {}

    return {
        "type": "Feature",
        "properties": {
            **custom_properties,
            "id": point.get("id", idx),
            "name": point.get("name") or f"Punto {idx + 1}",
            "type": point.get("type", "point"),
            "color": point.get("color", "#3b82f6"),
            "description": point.get("description", "")
        },
        "geometry": {
            "type": "Point",
            "coordinates": [lon, lat]
        }
    }


@router.post("/export")
async def export_geojson(req: ExportRequest):
    """Esporta le regioni in formato GeoJSON"""
    
    if req.session_id not in sessions:
        raise HTTPException(404, "Sessione non trovata")
    
    session = sessions[req.session_id]
    regions = session["regions"]
    
    georef = Georeferencer(
        session["width"],
        session["height"],
        req.bounds.model_dump()
    )

    if req.regions is not None or req.points is not None:
        features = []
        for i, region in enumerate(req.regions or []):
            feature = _client_region_to_feature(region, i, georef)
            if feature:
                features.append(feature)
        for i, point in enumerate(req.points or []):
            features.append(_client_point_to_feature(point, i, georef))

        if not features:
            raise HTTPException(400, "Nessun elemento valido da esportare")

        return {
            "type": "FeatureCollection",
            "properties": {
                "source": "Map to GeoJSON Converter",
                "bounds": req.bounds.model_dump(),
                "image_size": {"width": session["width"], "height": session["height"]}
            },
            "features": features
        }
    
    if not regions:
        raise HTTPException(400, "Nessuna regione da esportare")
    
    features = []
    for i, region in enumerate(regions):
        coords = georef.contour_to_coords(region.contour)
        
        name = region.name or f"Regione {i + 1}"
        if req.region_names:
            name = req.region_names.get(i) or req.region_names.get(str(i)) or name
        
        features.append({
            "type": "Feature",
            "properties": {
                "id": i,
                "name": name,
                "area_pixels": region.area,
                "color": f"#{region.color[2]:02x}{region.color[1]:02x}{region.color[0]:02x}"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [coords]
            }
        })
    
    return {
        "type": "FeatureCollection",
        "properties": {
            "source": "Map to GeoJSON Converter",
            "bounds": req.bounds.model_dump(),
            "image_size": {"width": session["width"], "height": session["height"]}
        },
        "features": features
    }


@router.get("/presets")
async def get_presets():
    """Restituisce i preset geografici disponibili"""
    return GEO_PRESETS
