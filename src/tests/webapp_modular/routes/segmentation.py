"""
🔍 Segmentation Routes
Endpoint per la segmentazione delle immagini

Author: Map to GeoJSON Converter Project
"""

from fastapi import APIRouter, HTTPException
import cv2
import numpy as np

from models import SegmentRequest, PointRequest, UpdateRegionRequest
from utils import image_to_base64, region_to_dict
from session_manager import sessions

router = APIRouter(prefix="/api", tags=["segmentation"])


@router.post("/segment")
async def segment_image(req: SegmentRequest):
    """Esegue la segmentazione automatica"""
    
    if req.session_id not in sessions:
        raise HTTPException(404, "Sessione non trovata")
    
    session = sessions[req.session_id]
    segmenter = session["segmenter"]
    
    try:
        regions = segmenter.segment(n_colors=req.n_colors, min_area=req.min_area)
        session["regions"] = regions
        
        vis = segmenter.visualize(regions)
        
        return {
            "success": True,
            "num_regions": len(regions),
            "regions": [region_to_dict(r, i) for i, r in enumerate(regions)],
            "visualization": image_to_base64(vis)
        }
    except Exception as e:
        raise HTTPException(500, f"Errore segmentazione: {str(e)}")


@router.post("/segment-point")
async def segment_at_point(req: PointRequest):
    """Segmenta una regione cliccando un punto"""
    
    if req.session_id not in sessions:
        raise HTTPException(404, "Sessione non trovata")
    
    session = sessions[req.session_id]
    segmenter = session["segmenter"]
    regions = session["regions"]
    
    new_region = segmenter.segment_at_point(req.x, req.y)
    
    if new_region:
        for existing in regions:
            point_inside_existing = cv2.pointPolygonTest(
                existing.contour.astype(np.float32),
                (float(req.x), float(req.y)),
                False
            ) >= 0
            centroid_inside_existing = cv2.pointPolygonTest(
                existing.contour.astype(np.float32),
                (float(new_region.centroid[0]), float(new_region.centroid[1])),
                False
            ) >= 0
            if (
                (point_inside_existing or centroid_inside_existing)
                and existing.area > new_region.area * 1.25
            ):
                return {
                    "success": False,
                    "message": "Il punto e' gia' dentro una regione esistente. Selezionala o eliminala prima di risegmentare."
                }

        regions.append(new_region)
        session["regions"] = regions
        
        vis = segmenter.visualize(regions)
        
        return {
            "success": True,
            "num_regions": len(regions),
            "regions": [region_to_dict(r, i) for i, r in enumerate(regions)],
            "visualization": image_to_base64(vis)
        }
    
    return {"success": False, "message": "Nessuna regione trovata in questo punto"}


@router.post("/delete-region/{region_id}")
async def delete_region(region_id: int, session_id: str):
    """Elimina una regione"""
    
    if session_id not in sessions:
        raise HTTPException(404, "Sessione non trovata")
    
    session = sessions[session_id]
    regions = session["regions"]
    
    if 0 <= region_id < len(regions):
        regions.pop(region_id)
        session["regions"] = regions
        
        vis = session["segmenter"].visualize(regions)
        
        return {
            "success": True,
            "regions": [region_to_dict(r, i) for i, r in enumerate(regions)],
            "visualization": image_to_base64(vis)
        }
    
    raise HTTPException(404, "Regione non trovata")


@router.post("/update-region")
async def update_region(req: UpdateRegionRequest):
    """Aggiorna i punti di una regione (editor poligoni)"""
    
    if req.session_id not in sessions:
        raise HTTPException(404, "Sessione non trovata")
    
    session = sessions[req.session_id]
    regions = session["regions"]
    
    if not (0 <= req.region_id < len(regions)):
        raise HTTPException(404, "Regione non trovata")
    
    # Aggiorna i punti del contorno
    new_contour = np.array(req.points, dtype=np.float32).reshape(-1, 1, 2)
    region = regions[req.region_id]
    region.contour = new_contour
    
    # Ricalcola centroid e area
    moments = cv2.moments(new_contour.astype(np.int32))
    if moments["m00"] != 0:
        region.centroid = (
            moments["m10"] / moments["m00"],
            moments["m01"] / moments["m00"]
        )
    region.area = cv2.contourArea(new_contour.astype(np.int32))
    
    # Ricalcola bounding box
    x, y, w, h = cv2.boundingRect(new_contour.astype(np.int32))
    region.bbox = (x, y, w, h)
    
    session["regions"] = regions
    
    vis = session["segmenter"].visualize(regions)
    
    return {
        "success": True,
        "regions": [region_to_dict(r, i) for i, r in enumerate(regions)],
        "visualization": image_to_base64(vis)
    }
