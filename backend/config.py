from pathlib import Path
from pydantic_settings import BaseSettings

_ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    use_mock: bool = True
    database_url: str = "sqlite:///./cosmic_mart.db"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    frontend_url: str = ""  # set in production, e.g. https://cosmic-mart.onrender.com

    @property
    def allowed_origins(self) -> list[str]:
        origins = list(self.cors_origins)
        if self.frontend_url and self.frontend_url not in origins:
            origins.append(self.frontend_url)
        return origins

    model_config = {"env_file": str(_ENV_FILE), "env_file_encoding": "utf-8"}


settings = Settings()
