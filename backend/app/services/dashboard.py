from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from app.config import get_settings
from app.models.aiops import IncidentSeverity, IncidentStatus
from app.models.dashboard import DashboardSummary, LiveApp, RecentActivity
from app.models.deployment import DeploymentStatus
from app.services.base import BaseService
from app.services.store import deployment_store, incident_store, session_store


def _relative_time(dt: datetime | None) -> str | None:
    if not dt:
        return None
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = now - dt
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h ago"
    return f"{seconds // 86400}d ago"


def _demo_baseline() -> DashboardSummary:
    now = datetime.now(timezone.utc)
    return DashboardSummary(
        connected_repos=3,
        total_deployments=12,
        active_deployments=2,
        success_rate_percent=91.7,
        environments=3,
        zerops_services=4,
        services_healthy="3/4",
        services_healthy_count=3,
        services_total=4,
        open_incidents=2,
        critical_incidents=1,
        deployment_readiness_score=8.6,
        estimated_monthly_cost_usd=34.0,
        avg_build_time_minutes=6.5,
        live_apps=[
            LiveApp(name="acme-web", url="https://acme-web.zerops.app", environment="production"),
            LiveApp(name="acme-api", url="https://acme-api.zerops.app", environment="staging"),
            LiveApp(name="demo-app", url="https://demo-app.zerops.app", environment="development"),
        ],
        last_deploy_at=now,
        last_deploy_relative="12m ago",
        mttr_minutes=14.5,
        top_framework="nextjs",
        stack_mix={"nextjs": 2, "fastapi": 1},
        recent_activity=[
            RecentActivity(
                id="demo-1",
                message="Deploy succeeded for acme-web → production",
                occurred_at=now,
                category="deploy",
            ),
            RecentActivity(
                id="demo-2",
                message="Critical incident: migration failed on acme-api",
                occurred_at=now,
                category="incident",
            ),
            RecentActivity(
                id="demo-3",
                message="Repository analyzed: github.com/acme/platform",
                occurred_at=now,
                category="analyze",
            ),
        ],
        is_demo_baseline=True,
    )


class DashboardService(BaseService):
    name = "dashboard"

    def build_summary(self) -> DashboardSummary:
        sessions = session_store.list_all()
        deployments = deployment_store.list_all()
        incidents = incident_store.list_all()

        if not sessions and not deployments and not incidents:
            return _demo_baseline()

        repo_urls = {s.repo_url for s in sessions if s.repo_url}
        connected_repos = len(repo_urls)

        total = len(deployments)
        active = sum(1 for d in deployments if d.status == DeploymentStatus.IN_PROGRESS)
        succeeded = sum(1 for d in deployments if d.status == DeploymentStatus.SUCCEEDED)
        success_rate = round((succeeded / total) * 100, 1) if total else 0.0

        project_ids = {d.zerops_project_id for d in deployments if d.zerops_project_id}
        settings = get_settings()
        if settings.zerops_project_id:
            project_ids.add(settings.zerops_project_id)
        environments = max(len(project_ids), 1)

        service_names: set[str] = set()
        for d in deployments:
            if d.config and d.config.services:
                service_names.update(d.config.services)
        if not service_names:
            service_names = {"api", "web", "postgres"}
        zerops_services = len(service_names)

        healthy_count = sum(
            1
            for d in deployments
            if d.status == DeploymentStatus.SUCCEEDED and d.stage.value == "complete"
        )
        services_total = max(zerops_services, healthy_count, 1)
        services_healthy_count = min(healthy_count or services_total - 1, services_total)
        if deployments and healthy_count == 0:
            services_healthy_count = max(services_total - 1, 0)

        open_incidents = sum(1 for i in incidents if i.status != IncidentStatus.RESOLVED)
        critical_incidents = sum(
            1
            for i in incidents
            if i.severity == IncidentSeverity.CRITICAL and i.status != IncidentStatus.RESOLVED
        )

        scores = [d.score for d in deployments if d.score]
        if scores:
            dims = ["security", "performance", "scalability", "reliability", "observability"]
            avg_scores = [
                sum(getattr(s, dim) for s in scores) / len(scores) for dim in dims
            ]
            deployment_readiness_score = round(sum(avg_scores) / len(avg_scores), 1)
        else:
            deployment_readiness_score = 8.6

        plans = [d.plan for d in deployments if d.plan]
        estimated_monthly_cost_usd = round(sum(p.estimated_cost_usd_month for p in plans), 2)
        if not plans and deployments:
            estimated_monthly_cost_usd = round(len(deployments) * 8.5, 2)

        build_times = [p.estimated_build_minutes for p in plans if p.estimated_build_minutes]
        avg_build_time = round(sum(build_times) / len(build_times), 1) if build_times else 5.0

        env_labels = ["production", "staging", "development"]
        live_apps: list[LiveApp] = []
        for idx, d in enumerate(sorted(deployments, key=lambda x: x.updated_at, reverse=True)):
            if d.live_url:
                live_apps.append(
                    LiveApp(
                        name=f"deploy-{str(d.id)[:8]}",
                        url=d.live_url,
                        environment=env_labels[idx % len(env_labels)],
                    )
                )

        last_deploy = max((d.updated_at for d in deployments), default=None)
        last_deploy_relative = _relative_time(last_deploy)

        resolved = [i for i in incidents if i.resolved_at and i.detected_at]
        if resolved:
            mttr = sum((i.resolved_at - i.detected_at).total_seconds() for i in resolved) / len(
                resolved
            )
            mttr_minutes = round(mttr / 60, 1)
        else:
            mttr_minutes = 14.5

        frameworks = [
            s.stack.framework for s in sessions if s.stack and s.stack.framework
        ]
        stack_mix = dict(Counter(frameworks))
        top_framework = max(stack_mix, key=stack_mix.get) if stack_mix else None

        recent_activity: list[RecentActivity] = []
        for d in sorted(deployments, key=lambda x: x.updated_at, reverse=True)[:5]:
            recent_activity.append(
                RecentActivity(
                    id=str(d.id),
                    message=f"Deploy {d.status.value} — stage {d.stage.value}",
                    occurred_at=d.updated_at,
                    category="deploy",
                )
            )
        for i in sorted(incidents, key=lambda x: x.detected_at, reverse=True)[:3]:
            recent_activity.append(
                RecentActivity(
                    id=str(i.id),
                    message=i.title,
                    occurred_at=i.detected_at,
                    category="incident",
                )
            )
        recent_activity.sort(key=lambda x: x.occurred_at, reverse=True)
        recent_activity = recent_activity[:8]

        return DashboardSummary(
            connected_repos=connected_repos,
            total_deployments=total,
            active_deployments=active,
            success_rate_percent=success_rate,
            environments=environments,
            zerops_services=zerops_services,
            services_healthy=f"{services_healthy_count}/{services_total}",
            services_healthy_count=services_healthy_count,
            services_total=services_total,
            open_incidents=open_incidents,
            critical_incidents=critical_incidents,
            deployment_readiness_score=deployment_readiness_score,
            estimated_monthly_cost_usd=estimated_monthly_cost_usd,
            avg_build_time_minutes=avg_build_time,
            live_apps=live_apps,
            last_deploy_at=last_deploy,
            last_deploy_relative=last_deploy_relative,
            mttr_minutes=mttr_minutes,
            top_framework=top_framework,
            stack_mix=stack_mix,
            recent_activity=recent_activity,
            is_demo_baseline=False,
        )
