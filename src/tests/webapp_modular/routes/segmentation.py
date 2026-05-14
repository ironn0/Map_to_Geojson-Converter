"""
🔍 Segmentation Routes
Endpoint per la segmentazione delle immagini

Author: Map to GeoJSON Converter Project
"""

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException
from models import (
    AddRegionRequest,
    ExtractedRegion,
    PointRequest,
    SegmentRequest,
    UpdateRegionRequest,
)
from session_manager import get_session
from utils import color_hex_to_bgr, image_to_base64, region_to_dict

router = APIRouter(prefix="/api", tags=["segmentation"])


@router.post("/segment")
async def segment_image(req: SegmentRequest):
    """Esegue la segmentazione automatica"""
    
    session = get_session(req.session_id)
    if session is None:
        raise HTTPException(404, "Sessione non trovata")

    segmenter = session["segmenter"]
    
    try:
        robust_settings = req.robust_settings.model_dump() if req.robust_settings else None
        regions = segmenter.segment(
            n_colors=req.n_colors,
            min_area=req.min_area,
            robust_mode=req.robust_mode,
            robust_settings=robust_settings,
        )
        session["regions"] = regions
        
        vis = segmenter.visualize(regions)
        
        return {
            "success": True,
            "num_regions": len(regions),
            "regions": [region_to_dict(r, i) for i, r in enumerate(regions)],
            "visualization": image_to_base64(vis),
            "profile": segmenter.last_profile,
        }
    except Exception as e:
        raise HTTPException(500, f"Errore segmentazione: {str(e)}")


@router.post("/segment-point")
async def segment_at_point(req: PointRequest):
    """Segmenta una regione cliccando un punto"""
    
    session = get_session(req.session_id)
    if session is None:
        raise HTTPException(404, "Sessione non trovata")

    segmenter = session["segmenter"]
    regions = session["regions"]
    
    new_region = segmenter.segment_at_point(req.x, req.y)
    
    if new_region:
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
    
    session = get_session(session_id)
    if session is None:
        raise HTTPException(404, "Sessione non trovata")

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
    
    session = get_session(req.session_id)
    if session is None:
        raise HTTPException(404, "Sessione non trovata")

    regions = session["regions"]
    
    if not (0 <= req.region_id < len(regions)):
        raise HTTPException(404, "Regione non trovata")
    
    new_contour = np.array(req.points, dtype=np.float32).reshape(-1, 1, 2)
    region = regions[req.region_id]
    _apply_contour(region, new_contour)
    
    session["regions"] = regions
    
    vis = session["segmenter"].visualize(regions)
    
    return {
        "success": True,
        "regions": [region_to_dict(r, i) for i, r in enumerate(regions)],
        "visualization": image_to_base64(vis)
    }


@router.post("/add-region")
async def add_region(req: AddRegionRequest):
    """Aggiunge una nuova regione al backend (single source of truth)."""

    session = get_session(req.session_id)
    if session is None:
        raise HTTPException(404, "Sessione non trovata")

    regions = session["regions"]
    contour = np.array(req.points, dtype=np.float32).reshape(-1, 1, 2)
    if contour.shape[0] < 3:
        raise HTTPException(400, "Servono almeno 3 punti per creare una regione")

    default_color = _sample_color(session["image"], contour)
    color = default_color
    if req.color:
        try:
            color = color_hex_to_bgr(req.color)
        except Exception:
            raise HTTPException(400, "Formato colore non valido")

    region = ExtractedRegion(
        contour=contour,
        centroid=(0.0, 0.0),
        area=0.0,
        bbox=(0, 0, 0, 0),
        color=color,
        name=req.name,
    )
    _apply_contour(region, contour)

    regions.append(region)
    session["regions"] = regions
    vis = session["segmenter"].visualize(regions)
    return {
        "success": True,
        "regions": [region_to_dict(r, i) for i, r in enumerate(regions)],
        "visualization": image_to_base64(vis),
    }


def _apply_contour(region: ExtractedRegion, contour: np.ndarray) -> None:
    contour_i32 = contour.astype(np.int32)
    region.contour = contour
    region.area = cv2.contourArea(contour_i32)

    moments = cv2.moments(contour_i32)
    if moments["m00"] != 0:
        region.centroid = (
            moments["m10"] / moments["m00"],
            moments["m01"] / moments["m00"],
        )
    else:
        region.centroid = tuple(contour.reshape(-1, 2).mean(axis=0))

    x, y, w, h = cv2.boundingRect(contour_i32)
    region.bbox = (x, y, w, h)


def _sample_color(image: np.ndarray, contour: np.ndarray) -> tuple:
    mask = np.zeros(image.shape[:2], dtype=np.uint8)
    cv2.drawContours(mask, [contour.astype(np.int32)], -1, 255, -1)
    bgr = cv2.mean(image, mask=mask)[:3]
    return (int(bgr[0]), int(bgr[1]), int(bgr[2]))
