"""
🎯 Alignment Routes
Endpoint per l'allineamento territoriale

Author: Map to GeoJSON Converter Project
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
import cv2
import json
import numpy as np

from models import AlignRequest
from georeferencing import Georeferencer, TerritoryAligner
from utils import image_to_base64, region_to_dict, validate_bounds, validate_contour
from session_manager import sessions

router = APIRouter(prefix="/api", tags=["alignment"])


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
    
    if not regions:
        raise HTTPException(400, "Nessuna regione da allineare")

    bounds_dict = req.bounds.model_dump()
    if not validate_bounds(bounds_dict):
        raise HTTPException(400, "Confini geografici non validi")
    
    # Crea georeferencer per convertire pixel -> coordinate
    try:
        georef = Georeferencer(
            session["width"],
            session["height"],
            bounds_dict
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    
    # Converti regioni in GeoJSON features
    features = []
    for i, region in enumerate(regions):
        if not validate_contour(region.contour):
            raise HTTPException(400, f"Contorno non valido per la regione {i}")

        try:
            coords = georef.contour_to_coords(region.contour)
        except ValueError as e:
            raise HTTPException(400, f"Errore geometria regione {i}: {str(e)}")

        features.append({
            "type": "Feature",
            "properties": {"id": i, "name": region.name or f"Regione {i + 1}"},
            "geometry": {"type": "Polygon", "coordinates": [coords]}
        })
    
    # Se c'è un GeoJSON di riferimento, usa TerritoryAligner
    if req.reference_geojson:
        aligner = TerritoryAligner(req.reference_geojson)
        aligned_features = aligner.align_all(features, req.snap_strength)
        
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
        "regions": [region_to_dict(r, i) for i, r in enumerate(regions)],
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
