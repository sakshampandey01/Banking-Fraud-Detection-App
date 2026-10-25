"""Domain errors -> uniform JSON {"error": {"code", "message"}} for the frontend."""
import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, OperationalError, SQLAlchemyError

log = logging.getLogger("fraud-api")


class DomainError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code, self.code, self.message = status_code, code, message


# SQLSTATE raised by sp_process_transaction  ->  (HTTP status, error code)
_SQLSTATE_MAP = {
    "FD001": (404, "ACCOUNT_NOT_FOUND"),
    "FD002": (423, "ACCOUNT_BLOCKED"),
    "FD003": (422, "INSUFFICIENT_FUNDS"),
    "FD004": (400, "UNKNOWN_TYPE"),
    "FD005": (422, "SAME_ACCOUNT"),
}


def translate_db_error(exc: DBAPIError) -> DomainError | None:
    state = getattr(exc.orig, "sqlstate", None)
    if state in _SQLSTATE_MAP:
        status, code = _SQLSTATE_MAP[state]
        message = str(exc.orig).split(":", 1)[-1].strip().splitlines()[0]
        return DomainError(status, code, message)
    return None


async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code,
                        content={"error": {"code": exc.code, "message": exc.message}})


async def db_error_handler(_: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Safety net for any database error a route did not handle itself.

    * known business SQLSTATEs (FD001..FD005) -> their mapped 4xx
    * connection / availability problems      -> 503 (frontend can show "try again")
    * anything else                           -> 500, details only in the server log
    """
    if isinstance(exc, DBAPIError):
        domain = translate_db_error(exc)
        if domain:
            return await domain_error_handler(_, domain)
    log.exception("Unhandled database error")
    if isinstance(exc, OperationalError):
        status, code, msg = 503, "DB_UNAVAILABLE", "Database is temporarily unavailable"
    else:
        status, code, msg = 500, "DB_ERROR", "Unexpected database error"
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": msg}})
