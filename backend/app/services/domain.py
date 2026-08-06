import json
import re
from pathlib import Path

from app.models.analysis import (
    ArchitectureEdge,
    ArchitectureGraph,
    ArchitectureNode,
    StackDetection,
    ValidationIssue,
    ValidationReport,
)
from app.models.deployment import DeploymentPlan, DeploymentPlanService, ZeropsConfig
from app.services.base import BaseService


class AnalysisService(BaseService):
    name = "analysis"

    def detect_stack(self, files: dict[str, str]) -> StackDetection:
        signals: dict = {}
        stack = StackDetection(raw_signals=signals)

        pkg = files.get("package.json") or next(
            (v for k, v in files.items() if k.endswith("package.json")), ""
        )
        if pkg:
            stack.has_frontend = True
            stack.language = "javascript"
            stack.package_manager = "npm"
            if "@next/" in pkg or '"next"' in pkg:
                stack.framework = "nextjs"
                stack.runtime = "nodejs@22"
                signals["framework"] = "nextjs"
            if "prisma" in pkg.lower():
                stack.database = "postgresql"
                signals["database"] = "prisma/postgresql"

        req = files.get("requirements.txt") or next(
            (v for k, v in files.items() if k.endswith("requirements.txt")), ""
        )
        if req:
            stack.has_backend = True
            stack.language = "python"
            if "fastapi" in req.lower():
                stack.framework = "fastapi"
                stack.runtime = "python@3.12"
                signals["framework"] = "fastapi"

        if any("redis" in v.lower() for v in files.values()):
            stack.cache = "redis"

        env_vars = set(re.findall(r"process\.env\.(\w+)|os\.environ\[['\"](\w+)['\"]\]", " ".join(files.values())))
        stack.detected_env_vars = sorted({a or b for a, b in env_vars if a or b})
        stack.confidence = 0.85 if stack.framework else 0.4
        return stack

    def build_architecture(self, stack: StackDetection) -> ArchitectureGraph:
        nodes: list[ArchitectureNode] = []
        edges: list[ArchitectureEdge] = []

        if stack.has_frontend:
            nodes.append(
                ArchitectureNode(
                    id="frontend",
                    label="Frontend",
                    type="frontend",
                    technology=stack.framework or "web",
                )
            )
        if stack.has_backend:
            nodes.append(
                ArchitectureNode(
                    id="api",
                    label="API",
                    type="api",
                    technology=stack.framework or "api",
                )
            )
            if stack.has_frontend:
                edges.append(ArchitectureEdge(source="frontend", target="api", label="HTTP"))
        if stack.database:
            nodes.append(
                ArchitectureNode(
                    id="database",
                    label="Database",
                    type="database",
                    technology=stack.database,
                )
            )
            if stack.has_backend:
                edges.append(ArchitectureEdge(source="api", target="database"))
        if stack.cache:
            nodes.append(
                ArchitectureNode(id="cache", label="Cache", type="cache", technology=stack.cache)
            )
            if stack.has_backend:
                edges.append(ArchitectureEdge(source="api", target="cache"))

        return ArchitectureGraph(nodes=nodes, edges=edges)


class PlannerService(BaseService):
    name = "planner"

    def build_plan(self, stack: StackDetection, graph: ArchitectureGraph) -> DeploymentPlan:
        services = [
            DeploymentPlanService(
                name=n.id,
                type=n.type,
                estimated_ram_gb=0.5 if n.type != "database" else 1.0,
                estimated_cpu=1.0,
            )
            for n in graph.nodes
        ]
        return DeploymentPlan(
            services=services,
            estimated_cost_usd_month=round(len(services) * 8.5, 2),
            estimated_build_minutes=max(3, len(services) * 2),
        )


class YamlGeneratorService(BaseService):
    name = "yaml_generator"

    def __init__(self, templates_dir: Path) -> None:
        self._templates_dir = templates_dir

    def generate(self, stack: StackDetection, repo_url: str | None) -> ZeropsConfig:
        template_name = "nextjs" if stack.framework == "nextjs" else "fastapi"
        template_path = self._templates_dir / "zerops" / f"{template_name}.yaml.j2"
        import_path = self._templates_dir / "zerops" / f"import_{template_name}.yaml.j2"

        zerops_yaml = self._load_template(template_path, stack, repo_url)
        import_yaml = self._load_template(import_path, stack, repo_url)

        return ZeropsConfig(
            zerops_yaml=zerops_yaml,
            import_yaml=import_yaml,
            services=[n for n in ["frontend", "api", "database", "cache"] if self._service_needed(n, stack)],
        )

    def validate(self, stack: StackDetection, config: ZeropsConfig) -> ValidationReport:
        issues: list[ValidationIssue] = []
        required = {"DATABASE_URL"} if stack.database else set()
        missing = required - set(stack.detected_env_vars)
        for var in missing:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    code="MISSING_ENV",
                    message=f"Environment variable {var} not detected in source — may need manual setup",
                    field=var,
                )
            )
        if "readiness" not in config.zerops_yaml:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    code="NO_READINESS",
                    message="No readiness check configured",
                )
            )
        errors = [i for i in issues if i.severity == "error"]
        return ValidationReport(passed=len(errors) == 0, issues=issues)

    def _load_template(self, path: Path, stack: StackDetection, repo_url: str | None) -> str:
        if path.exists():
            content = path.read_text(encoding="utf-8")
            return (
                content.replace("{{RUNTIME}}", stack.runtime or "nodejs@22")
                .replace("{{REPO_URL}}", repo_url or "https://github.com/example/app")
                .replace("{{FRAMEWORK}}", stack.framework or "app")
            )
        return f"# Template not found: {path.name}\nzerops: []\n"

    @staticmethod
    def _service_needed(name: str, stack: StackDetection) -> bool:
        mapping = {
            "frontend": stack.has_frontend,
            "api": stack.has_backend,
            "database": bool(stack.database),
            "cache": bool(stack.cache),
        }
        return mapping.get(name, False)


class ZeropsService(BaseService):
    name = "zerops"

    def __init__(self, settings) -> None:
        self._settings = settings

    async def deploy(self, config: ZeropsConfig, demo_mode: bool = False) -> dict:
        """Trigger Zerops deploy via zcli/API. MVP returns simulated stages."""
        if demo_mode:
            return {"simulated": True, "project_id": "demo-project"}
        return {"simulated": False, "project_id": self._settings.zerops_project_id or "pending"}

    async def fetch_metrics(self, deployment_id: str) -> list[dict]:
        return []

    async def fetch_logs(self, deployment_id: str, tail: int = 500) -> list[str]:
        return []
