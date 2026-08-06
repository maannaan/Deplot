from uuid import UUID

from app.models.aiops import AIOpsReport, Diagnosis, Incident, IncidentSeverity, IncidentStatus, Remediation
from app.models.observability import ObservabilitySnapshot, ServiceHealth, ServiceMetrics, TimelineEvent
from app.services.base import BaseService
from app.services.store import deployment_store, incident_store


class ObservabilityService(BaseService):
    name = "observability"

    async def get_snapshot(self, deployment_id: UUID) -> ObservabilitySnapshot:
        deployment = deployment_store.get(deployment_id)
        services = ["frontend", "api", "database"] if deployment else ["api"]
        return ObservabilitySnapshot(
            deployment_id=deployment_id,
            metrics=[
                ServiceMetrics(service=s, cpu_percent=12.5, memory_mb=256.0) for s in services
            ],
            health=[ServiceHealth(service=s, status="healthy", readiness_ok=True) for s in services],
            timeline=[],
        )

    async def append_event(self, event: TimelineEvent) -> TimelineEvent:
        snap = await self.get_snapshot(event.deployment_id)
        snap.timeline.append(event)
        return event


class AIOpsService(BaseService):
    name = "aiops"

    DEMO_DIAGNOSIS = Diagnosis(
        root_cause="Prisma migration failed",
        reason="DATABASE_URL environment variable is missing",
        impact="Backend cannot connect to PostgreSQL",
        confidence=0.96,
        suggested_fix="Set DATABASE_URL in Zerops service environment variables",
        log_summary="Migration exited with code 1: connection refused to database",
    )

    DEMO_RUNBOOK = [
        "Open Zerops project → api service → Environment variables",
        "Add DATABASE_URL referencing the postgres service hostname",
        "Redeploy the api service and wait for readiness check",
    ]

    async def create_incident(
        self,
        deployment_id: UUID,
        title: str,
        *,
        demo_mode: bool = False,
        affected_service: str = "api",
    ) -> Incident:
        incident = Incident(
            deployment_id=deployment_id,
            title=title,
            severity=IncidentSeverity.CRITICAL,
            affected_service=affected_service,
        )
        if demo_mode:
            incident.diagnosis = self.DEMO_DIAGNOSIS
            incident.runbook = self.DEMO_RUNBOOK
            incident.status = IncidentStatus.DIAGNOSED
            incident.suggested_remediation = Remediation(
                description="Add DATABASE_URL to api service",
                env_changes={"DATABASE_URL": "postgresql://user:pass@postgres:5432/app"},
                yaml_diff="+ env:\n+   DATABASE_URL: ${postgres.DATABASE_URL}",
            )
        incident_store.save(incident)
        return incident

    async def list_incidents(self, deployment_id: UUID) -> list[Incident]:
        return [i for i in incident_store.list_all() if i.deployment_id == deployment_id]

    async def get_incident(self, incident_id: UUID) -> Incident | None:
        return incident_store.get(incident_id)

    async def diagnose(self, incident: Incident, report: AIOpsReport | None = None) -> Incident:
        if report:
            incident.diagnosis = report.diagnosis
            incident.runbook = report.runbook
            incident.suggested_remediation = report.remediation
        incident.status = IncidentStatus.DIAGNOSED
        incident_store.save(incident)
        return incident

    async def resolve(self, incident_id: UUID) -> Incident | None:
        incident = incident_store.get(incident_id)
        if not incident:
            return None
        from datetime import datetime

        incident.status = IncidentStatus.RESOLVED
        incident.resolved_at = datetime.utcnow()
        incident_store.save(incident)
        return incident
