from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.agents.orchestrator import AgentContext
from app.api.deps import get_orchestrator
from app.bootstrap import get_service
from app.models.aiops import AIOpsReport, Incident

router = APIRouter()


@router.get("/deployment/{deployment_id}/incidents", response_model=list[Incident])
async def list_incidents(deployment_id: UUID):
    aiops = get_service("aiops")
    return await aiops.list_incidents(deployment_id)


@router.get("/incidents/{incident_id}", response_model=Incident)
async def get_incident(incident_id: UUID):
    aiops = get_service("aiops")
    incident = await aiops.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.post("/incidents/{incident_id}/diagnose", response_model=Incident)
async def diagnose_incident(incident_id: UUID):
    aiops = get_service("aiops")
    incident = await aiops.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    orchestrator = get_orchestrator()
    report: AIOpsReport = await orchestrator.run("aiops_analyst", AgentContext(payload={}))
    return await aiops.diagnose(incident, report)


@router.post("/incidents/{incident_id}/remediate", response_model=Incident)
async def remediate_incident(incident_id: UUID):
    aiops = get_service("aiops")
    incident = await aiops.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    from app.models.aiops import IncidentStatus

    incident.status = IncidentStatus.REMEDIATING
    return await aiops.resolve(incident_id) or incident


@router.post("/logs/analyze", response_model=AIOpsReport)
async def analyze_logs():
    orchestrator = get_orchestrator()
    return await orchestrator.run("aiops_analyst", AgentContext(payload={}))
