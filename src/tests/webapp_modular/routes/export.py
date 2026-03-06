"""
📦 Export Routes
Endpoint per l'esportazione GeoJSON

Author: Map to GeoJSON Converter Project
"""

from fastapi import APIRouter, HTTPException

from models import ExportRequest
from georeferencing import Georeferencer
from config import GEO_PRESETS
from session_manager import sessions

router = APIRouter(prefix="/api", tags=["export"])


@router.post("/export")
async def export_geojson(req: ExportRequest):
    """Esporta le regioni in formato GeoJSON"""
    
    if req.session_id not in sessions:
        raise HTTPException(404, "Sessione non trovata")
    
    session = sessions[req.session_id]
    regions = session["regions"]
    
    if not regions:
        raise HTTPException(400, "Nessuna regione da esportare")
    
    georef = Georeferencer(
        session["width"],
        session["height"],
        req.bounds.model_dump()
    )
    
    features = []
    for i, region in enumerate(regions):
        coords = georef.contour_to_coords(region.contour)
        
        name = region.name or f"Regione {i + 1}"
        if req.region_names and i in req.region_names:
            name = req.region_names[i]
        
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
            "bounds": req.bounds.model_dump()
        },
        "features": features
    }


@router.get("/presets")
async def get_presets():
    """Restituisce i preset geografici disponibili"""
    return GEO_PRESETS
