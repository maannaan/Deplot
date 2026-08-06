from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.agents.orchestrator import AgentContext
from app.api.deps import get_orchestrator
from app.bootstrap import get_service
from app.config import get_settings
from app.models.deployment import (
    DeployRequest,
    DeployResponse,
    Deployment,
    DeploymentScore,
    DeploymentStage,
    DeploymentStatus,
)
from app.services.store import deployment_store, session_store

router = APIRouter()


@router.post("/deploy", response_model=DeployResponse)
async def start_deploy(body: DeployRequest):
    session = session_store.get(body.session_id)
    if not session or not session.stack:
        raise HTTPException(status_code=404, detail="Session not found")

    yaml_svc = get_service("yaml_generator")
    zerops_svc = get_service("zerops")
    planner = get_service("planner")
    config = yaml_svc.generate(session.stack, session.repo_url)

    graph = session.architecture
    if not graph:
        orchestrator = get_orchestrator()
        graph = await orchestrator.run(
            "infrastructure_planner",
            AgentContext(payload={"stack": session.stack}),
        )

    plan = planner.build_plan(session.stack, graph)
    settings = get_settings()
    deployment = Deployment(
        session_id=body.session_id,
        config=config,
        plan=plan,
        zerops_project_id=settings.zerops_project_id or None,
    )
    deployment_store.save(deployment)

    await zerops_svc.deploy(config, demo_mode=body.demo_mode)

    deployment.status = DeploymentStatus.IN_PROGRESS
    deployment.stage = DeploymentStage.BUILDING
    deployment.live_url = "https://demo-app.zerops.app" if body.demo_mode else None
    deployment_store.save(deployment)

    if body.demo_mode:
        aiops = get_service("aiops")
        await aiops.create_incident(
            deployment.id,
            "Backend cannot start — migration failed",
            demo_mode=True,
        )

    return DeployResponse(
        deployment_id=deployment.id,
        status=deployment.status,
        stage=deployment.stage,
    )


@router.get("/deployment/{deployment_id}", response_model=Deployment)
async def get_deployment(deployment_id: UUID):
    deployment = deployment_store.get(deployment_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return deployment


@router.post("/deploy/{deployment_id}/redeploy", response_model=DeployResponse)
async def redeploy(deployment_id: UUID):
    deployment = deployment_store.get(deployment_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    deployment.status = DeploymentStatus.IN_PROGRESS
    deployment.stage = DeploymentStage.BUILDING
    deployment_store.save(deployment)

    deployment.status = DeploymentStatus.SUCCEEDED
    deployment.stage = DeploymentStage.COMPLETE
    deployment_store.save(deployment)

    return DeployResponse(
        deployment_id=deployment.id,
        status=deployment.status,
        stage=deployment.stage,
    )


@router.get("/deployment/{deployment_id}/score", response_model=DeploymentScore)
async def deployment_score(deployment_id: UUID):
    deployment = deployment_store.get(deployment_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    orchestrator = get_orchestrator()
    score = await orchestrator.run("optimization_advisor", AgentContext(payload={}))
    deployment.score = score
    deployment_store.save(deployment)
    return score
