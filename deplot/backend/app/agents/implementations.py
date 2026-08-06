from app.agents.base import AgentContext, BaseAgent
from app.agents.orchestrator import register_agent
from app.models.aiops import AIOpsReport
from app.models.analysis import ArchitectureGraph, StackDetection, ValidationReport
from app.models.deployment import DeploymentPlan, DeploymentScore, ZeropsConfig
from app.services.domain import AnalysisService, PlannerService, YamlGeneratorService


@register_agent
class RepositoryAnalyzerAgent(BaseAgent[StackDetection]):
    name = "repository_analyzer"
    prompt_file = "repository_analyzer.md"

    async def run(self, context: AgentContext) -> StackDetection:
        files = context.payload.get("files", {})
        service = AnalysisService()
        return service.detect_stack(files)


@register_agent
class InfrastructurePlannerAgent(BaseAgent[ArchitectureGraph]):
    name = "infrastructure_planner"
    prompt_file = "infrastructure_planner.md"

    async def run(self, context: AgentContext) -> ArchitectureGraph:
        stack: StackDetection = context.payload["stack"]
        service = AnalysisService()
        return service.build_architecture(stack)


@register_agent
class YamlGeneratorAgent(BaseAgent[ZeropsConfig]):
    name = "yaml_generator"
    prompt_file = "yaml_generator.md"

    async def run(self, context: AgentContext) -> ZeropsConfig:
        stack: StackDetection = context.payload["stack"]
        repo_url = context.payload.get("repo_url")
        service = YamlGeneratorService(self._settings.templates_dir)
        return service.generate(stack, repo_url)


@register_agent
class DeploymentValidatorAgent(BaseAgent[ValidationReport]):
    name = "deployment_validator"
    prompt_file = "deployment_validator.md"

    async def run(self, context: AgentContext) -> ValidationReport:
        stack: StackDetection = context.payload["stack"]
        config: ZeropsConfig = context.payload["config"]
        service = YamlGeneratorService(self._settings.templates_dir)
        return service.validate(stack, config)


@register_agent
class AIOpsAnalystAgent(BaseAgent[AIOpsReport]):
    name = "aiops_analyst"
    prompt_file = "aiops_analyst.md"

    async def run(self, context: AgentContext) -> AIOpsReport:
        from app.services.operations import AIOpsService

        svc = AIOpsService()
        from app.models.aiops import Remediation

        return AIOpsReport(
            diagnosis=svc.DEMO_DIAGNOSIS,
            runbook=svc.DEMO_RUNBOOK,
            remediation=Remediation(
                description="Add DATABASE_URL to api service",
                env_changes={"DATABASE_URL": "postgresql://user:pass@postgres:5432/app"},
            ),
            observability_gaps=["No readiness check on API", "No Redis cache configured"],
        )


@register_agent
class OptimizationAdvisorAgent(BaseAgent[DeploymentScore]):
    name = "optimization_advisor"
    prompt_file = "optimization_advisor.md"

    async def run(self, context: AgentContext) -> DeploymentScore:
        return DeploymentScore(
            security=9.2,
            performance=8.7,
            scalability=8.9,
            reliability=9.4,
            observability=7.8,
            recommendations=[
                "Add Redis cache for session storage",
                "Enable readiness checks on all runtime services",
                "Configure vertical autoscaling for API service",
            ],
        )
