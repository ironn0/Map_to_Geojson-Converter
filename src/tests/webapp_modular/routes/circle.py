"""
Circle detection routes.
"""

from fastapi import APIRouter, HTTPException
from georeferencing import Georeferencer, detect_and_georeference_circle
from models import CircleDetectRequest
from session_manager import get_session
from utils import validate_bounds

router = APIRouter(prefix="/api", tags=["circle"])


@router.post("/detect-circle")
async def detect_circle(req: CircleDetectRequest):
    session = get_session(req.session_id)
    if session is None:
        raise HTTPException(404, "Sessione non trovata")

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
        circle_result = detect_and_georeference_circle(
            session["image"],
            georef,
            strict_center_target_m=req.strict_center_target_m,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    session["detected_circle"] = circle_result
    return {
        "success": True,
        "circle": circle_result,
        "georeferencing": georef.get_transform_metrics(),
    }


@router.delete("/detect-circle/{session_id}")
async def clear_detected_circle(session_id: str):
    session = get_session(session_id)
    if session is None:
        raise HTTPException(404, "Sessione non trovata")
    session.pop("detected_circle", None)
    return {"success": True}
