"""Domain errors -> uniform JSON {"error": {"code", "message"}} for the frontend."""
import logging

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, OperationalError, SQLAlchemyError

log = logging.getLogger("fraud-api")


class DomainError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code, self.code, self.message = status_code, code, message


# SQLSTATE raised by sp_process_transaction / fn_open_account  ->  (HTTP status, error code)
_SQLSTATE_MAP = {
    "FD001": (404, "ACCOUNT_NOT_FOUND"),
    "FD002": (423, "ACCOUNT_BLOCKED"),
    "FD003": (422, "INSUFFICIENT_FUNDS"),
    "FD004": (400, "UNKNOWN_TYPE"),
    "FD005": (422, "SAME_ACCOUNT"),
    "FD006": (409, "ACCOUNT_EXISTS"),
    "22023": (422, "INVALID_INPUT"),         # invalid_parameter_value
}


def _db_message(exc: DBAPIError) -> str:
    """The message the procedure raised, without psycopg's CONTEXT / line decorations."""
    diag = getattr(exc.orig, "diag", None)
    primary = getattr(diag, "message_primary", None)
    return primary or str(exc.orig).strip().splitlines()[0]


def translate_db_error(exc: DBAPIError) -> DomainError | None:
    state = getattr(exc.orig, "sqlstate", None)
    if state in _SQLSTATE_MAP:
        status, code = _SQLSTATE_MAP[state]
        return DomainError(status, code, _db_message(exc))
    return None


async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code,
                        content={"error": {"code": exc.code, "message": exc.message}})


async def db_error_handler(_: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Safety net for any database error a route did not handle itself.

    * known business SQLSTATEs (FD001..FD006) -> their mapped 4xx
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


async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """422 in the same shape as every other error, with a readable message and per-field details."""
    fields = [
        {"field": ".".join(str(p) for p in err["loc"] if p not in ("body",)) or "request",
         "message": str(err["msg"])}
        for err in exc.errors()
    ]
    message = "; ".join(f"{f['field']}: {f['message']}" for f in fields[:3]) or "Invalid request"
    if len(fields) > 3:
        message += f" (+{len(fields) - 3} more)"
    return JSONResponse(status_code=422,
                        content={"error": {"code": "VALIDATION_ERROR", "message": message, "fields": fields}})


async def http_error_handler(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code,
                        content={"error": {"code": f"HTTP_{exc.status_code}", "message": str(exc.detail)}},
                        headers=getattr(exc, "headers", None))


async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
    log.exception("Unhandled error", exc_info=exc)
    return JSONResponse(status_code=500,
                        content={"error": {"code": "INTERNAL_ERROR", "message": "Unexpected server error"}})
