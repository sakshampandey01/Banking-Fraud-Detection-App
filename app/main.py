"""
FastAPI entry point.

Start:  uvicorn app.main:app --reload
Docs :  http://localhost:8000/docs
Health: http://localhost:8000/api/health   (says exactly what is missing, if anything)

The server always starts. If the model, preprocessing values or database are not ready, the
scoring endpoints answer HTTP 503 with instructions instead of the whole app crashing.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.database import dispose_engine, fetch_type_encoding, ping
from app.errors import (DomainError, db_error_handler, domain_error_handler, http_error_handler,
                        unhandled_error_handler, validation_error_handler)
from app.routers import accounts, predict, stats, transactions
from app.runtime import Runtime, ScoringUnavailable

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("fraud-api")
settings = get_settings()


def create_runtime() -> Runtime:
    runtime = Runtime(preprocessing_path=settings.resolved_preprocessing_path,
                      model_path=settings.resolved_model_path)
    runtime.load_artifacts()
    runtime.verify_database(fetch_type_encoding)
    for issue in runtime.scoring_issues():
        log.warning("NOT READY [%s] %s", issue.code, issue.message)
    if runtime.model and runtime.builder:
        log.info("Loaded %s (threshold=%.6f, features=%s)", runtime.model.name,
                 runtime.model.threshold, runtime.model.features)
    return runtime


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.runtime = create_runtime()
    yield
    dispose_engine()


async def scoring_unavailable_handler(_, exc: ScoringUnavailable) -> JSONResponse:
    first = exc.issues[0]
    return JSONResponse(status_code=503, content={"error": {
        "code": first.code, "message": first.message,
        "issues": [i.as_dict() for i in exc.issues]}})


app = FastAPI(title="Bank Fraud Detection API", version="1.1.0", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                   allow_methods=["*"], allow_headers=["*"])
app.add_exception_handler(DomainError, domain_error_handler)
app.add_exception_handler(ScoringUnavailable, scoring_unavailable_handler)
app.add_exception_handler(SQLAlchemyError, db_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(StarletteHTTPException, http_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)

app.include_router(transactions.router, prefix="/api")
app.include_router(predict.router, prefix="/api")
app.include_router(accounts.router, prefix="/api")
app.include_router(stats.router, prefix="/api")


@app.get("/api/health", tags=["health"])
def health():
    """Always HTTP 200 while the server is up; `ready_for_scoring` tells you whether predictions work."""
    runtime: Runtime = app.state.runtime
    db_ok = ping()
    if db_ok and not runtime.db_checked:
        runtime.verify_database(fetch_type_encoding)        # recovers automatically once the DB is set up
    model_issues = runtime.model_issues()
    issues = [i.as_dict() for i in runtime.scoring_issues()]
    if not db_ok and not any(i["code"].startswith("DB_") for i in issues):
        issues.append({"code": "DB_UNAVAILABLE", "message": "Cannot connect to PostgreSQL."})
    return {
        "status": "ok" if not issues else "degraded",
        "ready_for_scoring": not issues,
        "database": {"connected": db_ok, "type_encoding_verified": runtime.db_checked},
        "model": {
            "loaded": runtime.model is not None and runtime.builder is not None and not model_issues,
            "name": runtime.model.name if runtime.model else None,
            "threshold": runtime.model.threshold if runtime.model else None,
            "features": runtime.model.features if runtime.model else None,
        },
        "issues": issues,
    }
