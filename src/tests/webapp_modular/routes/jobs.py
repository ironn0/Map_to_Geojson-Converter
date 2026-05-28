"""
Job queue routes for background processing.
"""

from fastapi import APIRouter, HTTPException, Query
from georeferencing import Georeferencer, detect_and_georeference_circle
from job_manager import get_job, list_jobs, submit_job
from models import CircleDetectRequest, SegmentRequest
from session_manager import get_session
from utils import image_to_base64, region_to_dict, validate_bounds

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("/segment")
async def queue_segment(req: SegmentRequest):
    session = get_session(req.session_id)
    if session is None:
        raise HTTPException(404, "Sessione non trovata")

    def _task():
        robust_settings = req.robust_settings.model_dump() if req.robust_settings else None
        regions = session["segmenter"].segment(
            n_colors=req.n_colors,
            min_area=req.min_area,
            robust_mode=req.robust_mode,
            robust_settings=robust_settings,
        )
        session["regions"] = regions
        vis = session["segmenter"].visualize(regions)
        return {
            "success": True,
            "num_regions": len(regions),
            "regions": [region_to_dict(r, i) for i, r in enumerate(regions)],
            "visualization": image_to_base64(vis),
            "profile": session["segmenter"].last_profile,
        }

    job = submit_job(job_type="segment", session_id=req.session_id, fn=_task)
    return {"success": True, "job": job}


@router.post("/detect-circle")
async def queue_detect_circle(req: CircleDetectRequest):
    session = get_session(req.session_id)
    if session is None:
        raise HTTPException(404, "Sessione non trovata")
    bounds_dict = req.bounds.model_dump()
    if not validate_bounds(bounds_dict):
        raise HTTPException(400, "Confini geografici non validi")

    georeferencing_cfg = req.georeferencing.model_dump() if req.georeferencing else None

    def _task():
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
        session["detected_circle"] = circle_result
        return {
            "success": True,
            "circle": circle_result,
            "georeferencing": georef.get_transform_metrics(),
        }

    job = submit_job(job_type="detect-circle", session_id=req.session_id, fn=_task)
    return {"success": True, "job": job}


@router.get("/{job_id}")
async def job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job non trovato")
    return {"success": True, "job": job}


@router.get("")
async def list_jobs_route(
    session_id: str = Query(default=""),
    limit: int = Query(default=50, ge=1, le=500),
):
    items = list_jobs(session_id=session_id or None, limit=limit)
    return {"success": True, "jobs": items}
