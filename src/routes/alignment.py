"""
🎯 Alignment Routes
Endpoint per l'allineamento territoriale

Author: Map to GeoJSON Converter Project
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
import cv2
import json
import numpy as np
from typing import Optional

from models import AlignRequest
from georeferencing import Georeferencer, TerritoryAligner
from utils import image_to_base64, region_to_dict
from session_manager import sessions

router = APIRouter(prefix="/api", tags=["alignment"])


def _region_dict_to_feature(region: dict, idx: int, georef: Georeferencer) -> Optional[dict]:
    points = region.get("points") or []
    if len(points) < 3:
        return None
    coords = [list(georef.pixel_to_coord(float(p[0]), float(p[1]))) for p in points]
    if coords and coords[0] != coords[-1]:
        coords.append(coords[0])
    return {
        "type": "Feature",
        "properties": {
            "id": region.get("id", idx),
            "name": region.get("name") or f"Regione {idx + 1}",
            "color": region.get("color", "#3b82f6"),
            "type": region.get("type", "area")
        },
        "geometry": {"type": "Polygon", "coordinates": [coords]}
    }


def _feature_to_region_dict(feature: dict, idx: int, georef: Georeferencer) -> dict:
    coords = feature.get("geometry", {}).get("coordinates", [[]])[0]
    points = []
    for lon, lat in coords[:-1] if len(coords) > 1 else coords:
        px = (lon - georef.west) / georef.lon_per_pixel
        py = (georef.north - lat) / georef.lat_per_pixel
        points.append([px, py])
    props = feature.get("properties", {})
    return {
        "id": props.get("id", idx),
        "name": props.get("name") or f"Regione {idx + 1}",
        "color": props.get("color", "#3b82f6"),
        "points": points,
        "clientSide": True
    }


@router.post("/align")
async def align_territories(req: AlignRequest):
    """
    Allinea le regioni estratte ai confini geografici di riferimento.
    Può usare GeoJSON fornito dall'utente o scaricare da Natural Earth.
    """
    
    if req.session_id not in sessions:
        raise HTTPException(404, "Sessione non trovata")
    
    session = sessions[req.session_id]
    regions = session["regions"]
    
    if not regions and not req.regions:
        raise HTTPException(400, "Nessuna regione da allineare")
    
    # Crea georeferencer per convertire pixel -> coordinate
    georef = Georeferencer(
        session["width"],
        session["height"],
        req.bounds.model_dump()
    )
    
    features = []
    if req.regions is not None:
        for i, region in enumerate(req.regions):
            feature = _region_dict_to_feature(region, i, georef)
            if feature:
                features.append(feature)
    else:
        for i, region in enumerate(regions):
            coords = georef.contour_to_coords(region.contour)
            features.append({
                "type": "Feature",
                "properties": {
                    "id": i,
                    "name": region.name or f"Regione {i + 1}",
                    "color": f"#{region.color[2]:02x}{region.color[1]:02x}{region.color[0]:02x}"
                },
                "geometry": {"type": "Polygon", "coordinates": [coords]}
            })
    
    # Se c'è un GeoJSON di riferimento, usa TerritoryAligner
    if req.reference_geojson:
        aligner = TerritoryAligner(req.reference_geojson)
        aligned_features = aligner.align_all(features, req.snap_strength)

        if req.regions is not None:
            return {
                "success": True,
                "message": f"Allineate {len(aligned_features)} regioni al riferimento",
                "regions": [_feature_to_region_dict(feat, i, georef) for i, feat in enumerate(aligned_features)],
                "aligned_geojson": {
                    "type": "FeatureCollection",
                    "features": aligned_features
                }
            }
        
        # Converti coordinate allineate in pixel e aggiorna le regioni
        for i, (feat, region) in enumerate(zip(aligned_features, regions)):
            aligned_coords = feat['geometry']['coordinates'][0]
            
            # Converti coord -> pixel
            new_points = []
            for lon, lat in aligned_coords[:-1]:  # Escludi ultimo punto (duplicato)
                px = (lon - georef.west) / georef.lon_per_pixel
                py = (georef.north - lat) / georef.lat_per_pixel
                new_points.append([px, py])
            
            if new_points:
                new_contour = np.array(new_points, dtype=np.float32).reshape(-1, 1, 2)
                region.contour = new_contour
                
                # Ricalcola proprietà
                moments = cv2.moments(new_contour.astype(np.int32))
                if moments["m00"] != 0:
                    region.centroid = (
                        moments["m10"] / moments["m00"],
                        moments["m01"] / moments["m00"]
                    )
                region.area = cv2.contourArea(new_contour.astype(np.int32))
                x, y, w, h = cv2.boundingRect(new_contour.astype(np.int32))
                region.bbox = (x, y, w, h)
        
        session["regions"] = regions
        vis = session["segmenter"].visualize(regions)
        
        return {
            "success": True,
            "message": f"Allineate {len(regions)} regioni al riferimento",
            "regions": [region_to_dict(r, i) for i, r in enumerate(regions)],
            "visualization": image_to_base64(vis),
            "aligned_geojson": {
                "type": "FeatureCollection",
                "features": aligned_features
            }
        }
    
    # Senza riferimento, restituisce le features convertite
    return {
        "success": True,
        "message": "Regioni convertite (nessun riferimento per allineamento)",
        "regions": req.regions if req.regions is not None else [region_to_dict(r, i) for i, r in enumerate(regions)],
        "geojson": {
            "type": "FeatureCollection", 
            "features": features
        }
    }


@router.post("/upload-reference")
async def upload_reference_geojson(file: UploadFile = File(...)):
    """Carica un file GeoJSON di riferimento per l'allineamento"""
    
    if not file.filename.endswith(('.geojson', '.json')):
        raise HTTPException(400, "Il file deve essere GeoJSON (.geojson o .json)")
    
    try:
        content = await file.read()
        geojson = json.loads(content.decode('utf-8'))
        
        # Valida la struttura
        if geojson.get('type') not in ['FeatureCollection', 'Feature']:
            raise HTTPException(400, "GeoJSON non valido: deve essere Feature o FeatureCollection")
        
        features = geojson.get('features', [geojson]) if geojson.get('type') == 'FeatureCollection' else [geojson]
        
        return {
            "success": True,
            "filename": file.filename,
            "num_features": len(features),
            "geojson": geojson
        }
    except json.JSONDecodeError:
        raise HTTPException(400, "File JSON non valido")
    except Exception as e:
        raise HTTPException(500, f"Errore nel parsing del GeoJSON: {str(e)}")
