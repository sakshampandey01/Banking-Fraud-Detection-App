"""Central configuration. Values come from environment variables or a .env file."""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", protected_namespaces=())

    # SQLAlchemy URL, e.g. postgresql+psycopg://user:pass@localhost:5432/fraud_db
    database_url: str = "postgresql+psycopg://fraud_user:fraud_pass@localhost:5432/fraud_db"

    # ML artifacts
    model_path: str = "models/best_fraud_model_tuned.pkl"
    preprocessing_path: str = "models/preprocessing.json"

    # probability >= model threshold (stored in the .pkl) => HIGH
    # probability >= medium_risk_threshold                 => MEDIUM
    medium_risk_threshold: float = Field(0.5, ge=0, le=1)

    # React dev servers (Vite = 5173, CRA = 3000)
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    @property
    def psycopg_dsn(self) -> str:
        """Plain libpq URL for scripts that use psycopg directly."""
        return self.database_url.replace("postgresql+psycopg://", "postgresql://")


@lru_cache
def get_settings() -> Settings:
    return Settings()
