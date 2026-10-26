"""Central configuration. Values come from environment variables or a .env file in the project root."""
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root (the folder that contains app/, models/, sql/ ...). Paths below are resolved
# against it, so the server works no matter which directory it is started from.
BASE_DIR = Path(__file__).resolve().parent.parent

# The notebook saves the artifact next to itself (project root); the app also accepts models/.
MODEL_FILENAME = "best_fraud_model_tuned.pkl"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore", protected_namespaces=())

    # SQLAlchemy URL, e.g. postgresql+psycopg://user:password@localhost:5432/fraud_db
    # Default = local Postgres, current OS user, no password (what Homebrew's PostgreSQL gives you).
    database_url: str = "postgresql+psycopg://localhost:5432/fraud_db"

    # ML artifacts (relative paths are resolved against the project root)
    model_path: str = f"models/{MODEL_FILENAME}"
    preprocessing_path: str = "models/preprocessing.json"

    # probability >= model threshold (stored in the .pkl) => HIGH
    # probability >= medium_risk_threshold                 => MEDIUM
    medium_risk_threshold: float = Field(0.5, ge=0, le=1)

    # React dev servers (Vite = 5173, CRA = 3000). In .env this must be JSON: ["http://localhost:5173"]
    cors_origins: list[str] = [
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:3000", "http://127.0.0.1:3000",
    ]

    @property
    def psycopg_dsn(self) -> str:
        """Plain libpq URL for scripts that use psycopg directly."""
        return self.database_url.replace("postgresql+psycopg://", "postgresql://")

    @property
    def resolved_preprocessing_path(self) -> Path:
        return _resolve(self.preprocessing_path)

    @property
    def resolved_model_path(self) -> Path:
        """Configured path if it exists, else the usual alternative locations, else the configured path."""
        configured = _resolve(self.model_path)
        if configured.exists():
            return configured
        for candidate in (BASE_DIR / MODEL_FILENAME, BASE_DIR / "models" / MODEL_FILENAME):
            if candidate.exists():
                return candidate
        return configured


def _resolve(path: str) -> Path:
    p = Path(path).expanduser()
    return p if p.is_absolute() else BASE_DIR / p


@lru_cache
def get_settings() -> Settings:
    return Settings()
