from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "employee-work-report"
    app_env: str = "development"
    database_url: str
    frontend_origins: str = "http://127.0.0.1:8080,http://localhost:8080"
    session_cookie_name: str = "employee_work_session"
    session_ttl_seconds: int = 60 * 60 * 12
    session_cookie_secure: bool | None = None
    password_view_secret: str | None = None
    login_max_failures: int = 5
    login_lockout_seconds: int = 15 * 60

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]

    @property
    def use_secure_session_cookie(self) -> bool:
        if self.session_cookie_secure is not None:
            return self.session_cookie_secure
        return self.app_env == "production"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
