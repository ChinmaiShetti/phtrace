from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_admin_user: str = "postgres"
    pg_admin_password: str = ""
    db_name: str = "pharmatrace"
    pg_owner_password: str = "owner_dev_password"
    pg_app_password: str = "app_dev_password"

    jwt_secret: str = "dev-only-secret-change-me-0123456789abcdef"
    jwt_expire_minutes: int = 480
    cors_origins: str = "http://localhost:5173"

    def url(self, user: str, password: str, db: str | None = None) -> str:
        return f"postgresql://{user}:{password}@{self.pg_host}:{self.pg_port}/{db or self.db_name}"

    @property
    def admin_url(self) -> str:
        return self.url(self.pg_admin_user, self.pg_admin_password, "postgres")

    @property
    def owner_url(self) -> str:
        return self.url("pharmatrace_owner", self.pg_owner_password)

    @property
    def app_url(self) -> str:
        return self.url("pharmatrace_app", self.pg_app_password)


@lru_cache
def get_settings() -> Settings:
    return Settings()
