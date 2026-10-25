"""SQLAlchemy engine (Core, no ORM): the schema is owned by the SQL scripts in /sql."""
from sqlalchemy import Engine, create_engine

from app.config import get_settings

_engine: Engine | None = None


def get_engine() -> Engine:
    """Create the engine lazily (one connection pool per process)."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            get_settings().database_url,
            pool_size=10,
            max_overflow=10,
            pool_pre_ping=True,   # drop dead connections transparently
        )
    return _engine
