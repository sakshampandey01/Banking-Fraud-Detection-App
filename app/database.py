"""SQLAlchemy engine (Core, no ORM): the schema is owned by the SQL scripts in /sql."""
import logging

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError, SQLAlchemyError

from app.config import get_settings
from app.runtime import DatabaseProblem

log = logging.getLogger("fraud-api")

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
            connect_args={"connect_timeout": 5},   # fail fast (seconds) instead of hanging when Postgres is down
        )
    return _engine


def dispose_engine() -> None:
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None


def ping() -> bool:
    """True if the database answers a trivial query."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        log.warning("Database ping failed", exc_info=True)
        return False


def fetch_type_encoding() -> dict[str, int]:
    """transaction_types as {type_code: type_enc}; raises DatabaseProblem with an actionable message."""
    try:
        with get_engine().connect() as conn:
            rows = conn.execute(text("SELECT type_code, type_enc FROM transaction_types")).all()
    except OperationalError as exc:
        log.warning("Cannot connect to the database", exc_info=True)
        raise DatabaseProblem(
            "DB_UNAVAILABLE",
            "Cannot connect to PostgreSQL. Check that it is running and that DATABASE_URL in .env is correct.") from exc
    except ProgrammingError as exc:
        if getattr(exc.orig, "sqlstate", None) == "42P01":          # undefined_table
            raise DatabaseProblem(
                "DB_SCHEMA_MISSING",
                "The database has no tables yet. Run `python scripts/init_db.py` once.") from exc
        log.exception("Unexpected SQL error while reading transaction_types")
        raise DatabaseProblem("DB_ERROR", "Unexpected database error; see the server log.") from exc
    except SQLAlchemyError as exc:
        log.exception("Unexpected database error")
        raise DatabaseProblem("DB_ERROR", "Unexpected database error; see the server log.") from exc
    return {str(code): int(enc) for code, enc in rows}
