"""Register all services and import agents for side-effect registration."""

from app.config import Settings, get_settings
from app.core.registry import service_registry
from app.services.domain import (
    AnalysisService,
    PlannerService,
    YamlGeneratorService,
    ZeropsService,
)
from app.services.github import GitHubService
from app.services.dashboard import DashboardService
from app.services.operations import AIOpsService, ObservabilityService


def bootstrap(settings: Settings | None = None) -> None:
    settings = settings or get_settings()

    if service_registry.keys():
        return

    service_registry.register("github", GitHubService(settings))
    service_registry.register("analysis", AnalysisService())
    service_registry.register("planner", PlannerService())
    service_registry.register("yaml_generator", YamlGeneratorService(settings.templates_dir))
    service_registry.register("zerops", ZeropsService(settings))
    service_registry.register("observability", ObservabilityService())
    service_registry.register("aiops", AIOpsService())
    service_registry.register("dashboard", DashboardService())

    # Import agents to trigger @register_agent decorators
    import app.agents.implementations  # noqa: F401


def get_service(name: str):
    return service_registry.get(name)
