"""
Operational observability routes.
"""

from fastapi import APIRouter, Query
from ops_log import list_errors, list_events

router = APIRouter(prefix="/api/ops", tags=["ops"])


@router.get("/errors")
async def get_errors(limit: int = Query(default=100, ge=1, le=500)):
    return {"success": True, "errors": list_errors(limit)}


@router.get("/events")
async def get_events(limit: int = Query(default=100, ge=1, le=500)):
    return {"success": True, "events": list_events(limit)}
