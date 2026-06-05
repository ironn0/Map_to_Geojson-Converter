"""
🔍 Segmentation Routes
Endpoint per la segmentazione delle immagini

Author: Map to GeoJSON Converter Project
"""

from fastapi import APIRouter, HTTPException
import cv2
import numpy as np

from models import (
    SegmentRequest, PointRequest, EraseSegmentRequest, BrushResegmentRequest,
    UpdateRegionRequest
)
from segmentation import MapSegmenter
from utils import image_to_base64, region_to_dict
from session_manager import sessions

router = APIRouter(prefix="/api", tags=["segmentation"])


def _strokes_to_mask(strokes, width: int, height: int, radius: int) -> np.ndarray:
    mask = np.zeros((height, width), dtype=np.uint8)
    brush_radius = max(3, min(int(radius), 120))

    for stroke in strokes:
        points = []
        for point in stroke:
            if len(point) < 2:
                continue
            x = int(round(max(0, min(width - 1, float(point[0])))))
            y = int(round(max(0, min(height - 1, float(point[1])))))
            points.append((x, y))

        if not points:
            continue

        if len(points) == 1:
            cv2.circle(mask, points[0], brush_radius, 255, -1)
            continue

        for start, end in zip(points, points[1:]):
            cv2.line(mask, start, end, 255, brush_radius * 2, cv2.LINE_AA)
        for point in points:
            cv2.circle(mask, point, brush_radius, 255, -1)

    return mask


def _region_to_mask(region: dict, width: int, height: int) -> np.ndarray:
    points = region.get("points") or []
    mask = np.zeros((height, width), dtype=np.uint8)
    if len(points) < 3:
        return mask

    contour = np.array(
        [[
            int(round(max(0, min(width - 1, float(point[0]))))),
            int(round(max(0, min(height - 1, float(point[1])))))
        ] for point in points],
        dtype=np.int32
    )
    cv2.fillPoly(mask, [contour], 255)
    return mask


def _mask_to_single_region_dict(mask: np.ndarray, original: dict, region_id: int, seed: tuple[int, int]) -> dict | None:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    containing = [
        contour for contour in contours
        if cv2.pointPolygonTest(contour, (float(seed[0]), float(seed[1])), False) >= 0
    ]
    contour = max(containing or contours, key=cv2.contourArea)
    area = float(cv2.contourArea(contour))
    if area < 12:
        return None

    epsilon = max(1.0, 0.005 * cv2.arcLength(contour, True))
    approx = cv2.approxPolyDP(contour, epsilon, True)
    if len(approx) < 3:
        return None

    return {
        **original,
        "id": region_id,
        "area": area,
        "points": [[float(p[0][0]), float(p[0][1])] for p in approx],
    }


def _choose_seed(region_mask: np.ndarray, negative_mask: np.ndarray) -> tuple[int, int] | None:
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    blocked = cv2.dilate(negative_mask, kernel, iterations=2)
    valid = cv2.bitwise_and(region_mask, cv2.bitwise_not(blocked))

    if cv2.countNonZero(valid) == 0:
        valid = cv2.bitwise_and(region_mask, cv2.bitwise_not(negative_mask))
    if cv2.countNonZero(valid) == 0:
        return None

    distance = cv2.distanceTransform(valid, cv2.DIST_L2, 5)
    _, _, _, max_loc = cv2.minMaxLoc(distance)
    return int(max_loc[0]), int(max_loc[1])


def _keep_seed_component(mask: np.ndarray, seed: tuple[int, int]) -> np.ndarray:
    """Tiene solo la componente connessa al seed buono."""
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    if num_labels <= 1:
        return mask

    x, y = seed
    if not (0 <= y < labels.shape[0] and 0 <= x < labels.shape[1]):
        return mask

    seed_label = labels[y, x]
    if seed_label == 0:
        candidate_labels = [
            label for label in range(1, num_labels)
            if stats[label, cv2.CC_STAT_AREA] > 0
        ]
        if not candidate_labels:
            return np.zeros_like(mask)
        seed_label = max(candidate_labels, key=lambda label: stats[label, cv2.CC_STAT_AREA])

    kept = np.zeros_like(mask)
    kept[labels == seed_label] = 255
    return kept


def _expanded_forbidden_mask(negative_mask: np.ndarray, radius: int) -> np.ndarray:
    """Allarga l'area negativa per separare lobi/sporgenze indesiderate."""
    size = max(15, int(radius * 2.5) + 1)
    if size % 2 == 0:
        size += 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))
    return cv2.dilate(negative_mask, kernel, iterations=1)


def _region_context_mask(region_mask: np.ndarray, radius: int) -> np.ndarray:
    """Consente una piccola espansione durante la risegmentazione guidata."""
    size = max(9, int(radius) * 2 + 1)
    if size % 2 == 0:
        size += 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))
    return cv2.dilate(region_mask, kernel, iterations=1)


def _select_region_index(regions: list[dict], selected_region_id: int | None, brush_mask: np.ndarray, width: int, height: int) -> int | None:
    if selected_region_id is not None and 0 <= int(selected_region_id) < len(regions):
        return int(selected_region_id)

    best_idx = None
    best_overlap = 0
    for idx, region in enumerate(regions):
        overlap = cv2.countNonZero(cv2.bitwise_and(_region_to_mask(region, width, height), brush_mask))
        if overlap > best_overlap:
            best_idx = idx
            best_overlap = overlap

    return best_idx if best_overlap > 0 else None


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


@router.post("/erase-and-segment")
async def erase_and_segment(req: EraseSegmentRequest):
    """Cancella dettagli raster indicati dall'utente e rilancia la segmentazione."""

    if req.session_id not in sessions:
        raise HTTPException(404, "Sessione non trovata")

    session = sessions[req.session_id]
    image = session["image"]
    height, width = image.shape[:2]

    radius = max(3, min(int(req.radius), 120))
    erase_mask = _strokes_to_mask(req.strokes, width, height, radius)

    if cv2.countNonZero(erase_mask) == 0:
        return {
            "success": False,
            "message": "Nessuna area cancellata"
        }

    if req.mode == "restore":
        original = session.get("original_image")
        if original is None:
            original = image
        corrected = image.copy()
        corrected[erase_mask > 0] = original[erase_mask > 0]
    else:
        corrected = cv2.inpaint(image, erase_mask, max(3, radius), cv2.INPAINT_TELEA)

    segmenter = MapSegmenter(corrected)
    regions = segmenter.segment(n_colors=req.n_colors, min_area=req.min_area)

    session["image"] = corrected
    session["segmenter"] = segmenter
    session["regions"] = regions

    vis = segmenter.visualize(regions)

    return {
        "success": True,
        "num_regions": len(regions),
        "regions": [region_to_dict(r, i) for i, r in enumerate(regions)],
        "image": image_to_base64(corrected),
        "visualization": image_to_base64(vis)
    }


@router.post("/resegment-with-brush")
async def resegment_with_brush(req: BrushResegmentRequest):
    """Risegmenta una regione ignorando l'area evidenziata col pennello."""

    if req.session_id not in sessions:
        raise HTTPException(404, "Sessione non trovata")

    session = sessions[req.session_id]
    image = session["image"]
    height, width = image.shape[:2]
    radius = max(3, min(int(req.radius), 120))
    negative_mask = _strokes_to_mask(req.strokes, width, height, radius)

    if cv2.countNonZero(negative_mask) == 0:
        return {
            "success": False,
            "message": "Nessuna area evidenziata"
        }

    target_idx = _select_region_index(req.regions, req.selected_region_id, negative_mask, width, height)
    if target_idx is None:
        return {
            "success": False,
            "message": "Seleziona una regione o pennella dentro una regione"
        }

    target_region = req.regions[target_idx]
    target_mask = _region_to_mask(target_region, width, height)
    seed = _choose_seed(target_mask, negative_mask)
    if seed is None:
        return {
            "success": False,
            "message": "Non resta un punto valido per risegmentare questa regione"
        }

    corrected = cv2.inpaint(image, negative_mask, max(3, radius), cv2.INPAINT_TELEA)
    segmenter = MapSegmenter(corrected)
    new_region = segmenter.segment_at_point(seed[0], seed[1])
    if new_region is None:
        return {
            "success": False,
            "message": "La risegmentazione guidata non ha trovato una nuova regione"
        }

    new_mask = np.zeros((height, width), dtype=np.uint8)
    cv2.drawContours(new_mask, [new_region.contour.astype(np.int32)], 0, 255, -1)
    # La pennellata e' una barriera negativa: non deve rientrare nella
    # regione e deve separare eventuali sporgenze attaccate, come label.
    forbidden = _expanded_forbidden_mask(negative_mask, radius)
    target_mask = _region_to_mask(target_region, width, height)
    context_mask = _region_context_mask(target_mask, radius)
    new_mask = cv2.bitwise_and(new_mask, context_mask)
    new_mask = cv2.bitwise_and(new_mask, cv2.bitwise_not(forbidden))
    new_mask = _keep_seed_component(new_mask, seed)
    close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    new_mask = cv2.morphologyEx(new_mask, cv2.MORPH_CLOSE, close_kernel, iterations=1)

    replacement = _mask_to_single_region_dict(new_mask, target_region, target_idx, seed)
    if replacement is None:
        return {
            "success": False,
            "message": "La nuova regione non e' valida"
        }

    updated_regions = []
    for idx, region in enumerate(req.regions):
        updated = replacement if idx == target_idx else {**region}
        updated["id"] = len(updated_regions)
        updated_regions.append(updated)

    session["image"] = corrected
    session["segmenter"] = segmenter

    return {
        "success": True,
        "num_regions": len(updated_regions),
        "regions": updated_regions,
        "selected_region_id": target_idx,
        "seed": [seed[0], seed[1]],
        "image": image_to_base64(corrected)
    }


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
