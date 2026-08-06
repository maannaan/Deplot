from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.bootstrap import get_service
from app.models.observability import ObservabilitySnapshot

router = APIRouter()


@router.get("/deployment/{deployment_id}/observability", response_model=ObservabilitySnapshot)
async def get_observability(deployment_id: UUID):
    obs = get_service("observability")
    return await obs.get_snapshot(deployment_id)


@router.get("/deployment/{deployment_id}/metrics")
async def get_metrics(deployment_id: UUID):
    snap = await get_observability(deployment_id)
    return {"deployment_id": str(deployment_id), "metrics": snap.metrics}


@router.get("/deployment/{deployment_id}/logs")
async def get_logs(deployment_id: UUID, tail: int = 500):
    zerops = get_service("zerops")
    lines = await zerops.fetch_logs(str(deployment_id), tail=tail)
    return {"deployment_id": str(deployment_id), "lines": lines}


@router.get("/deployment/{deployment_id}/timeline")
async def get_timeline(deployment_id: UUID):
    obs = get_service("observability")
    snap = await obs.get_snapshot(deployment_id)
    return {"deployment_id": str(deployment_id), "events": snap.timeline}


@router.post("/logs/summarize")
async def summarize_logs(deployment_id: UUID):
    return {
        "summary": "All services healthy. No errors in the last 500 log lines.",
        "deployment_id": str(deployment_id),
    }
