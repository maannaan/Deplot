from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root: monorepo parent locally, /var/www when prompts/ is co-deployed on Zerops
_backend_root = Path(__file__).resolve().parents[1]
if (_backend_root / "prompts").exists():
    REPO_ROOT = _backend_root
elif (_backend_root.parent / "prompts").exists():
    REPO_ROOT = _backend_root.parent
else:
    REPO_ROOT = _backend_root.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", str(REPO_ROOT / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Deplot AI"
    app_version: str = "0.1.0"
    debug: bool = False
    api_prefix: str = "/api/v1"

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    database_url: str = "postgresql+asyncpg://deplot:deplot@localhost:5432/deplot"
    redis_url: str = "redis://localhost:6379/0"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    github_token: str = ""

    zerops_api_token: str = ""
    zerops_project_id: str = ""
    zerops_deploy_project_id: str = ""
    zerops_api_base: str = "https://api.app-prg1.zerops.io/api/rest/public"
    zcli_path: str = ""
    search_heavy_stack: bool = True

    prompts_dir: Path = REPO_ROOT / "prompts"
    templates_dir: Path = REPO_ROOT / "templates"

    demo_mode_enabled: bool = True
    ai_agents_enabled: bool = True
    observability_poll_interval_seconds: int = 30
    remediation_timeout_seconds: int = 180
    remediation_poll_interval_seconds: int = 5

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def zerops_target_project_id(self) -> str:
        """Project used for wizard deploys (customer/showcase repos)."""
        return self.zerops_deploy_project_id or self.zerops_project_id

    @property
    def deploy_project_isolated(self) -> bool:
        """True when deploy sandbox is a separate project from the Deplot platform."""
        return bool(
            self.zerops_deploy_project_id
            and self.zerops_project_id
            and self.zerops_deploy_project_id != self.zerops_project_id
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
