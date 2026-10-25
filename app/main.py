"""
FastAPI entry point.

Start:  uvicorn app.main:app --reload
Docs :  http://localhost:8000/docs
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.database import get_engine
from app.errors import DomainError, db_error_handler, domain_error_handler
from app.ml.features import FeatureBuilder
from app.ml.model_service import FraudModel
from app.routers import accounts, stats, transactions

log = logging.getLogger("fraud-api")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once when the server starts: load the ML artifacts into memory."""
    # 1. model + preprocessing are loaded ONCE and shared by every request
    app.state.model = FraudModel.load(settings.model_path)
    app.state.builder = FeatureBuilder(settings.preprocessing_path)
    log.info("Loaded %s (threshold=%.4f, features=%s)",
             app.state.model.name, app.state.model.threshold, app.state.model.features)

    # 2. the feature order must match what the model was trained on
    if app.state.model.features != app.state.builder.features:
        raise RuntimeError("preprocessing.json features differ from the model's features")

    # 3. fail fast if the DB's transaction_types encoding drifted from the notebook's LabelEncoder
    with get_engine().connect() as conn:
        db_enc = dict(conn.execute(text("SELECT type_code, type_enc FROM transaction_types")).all())
    if db_enc != app.state.builder.type_encoding:
        raise RuntimeError(f"transaction_types ({db_enc}) != model encoding ({app.state.builder.type_encoding})")

    yield
    get_engine().dispose()          # shutdown: close pooled connections


app = FastAPI(title="Bank Fraud Detection API", version="1.0.0", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                   allow_methods=["*"], allow_headers=["*"])
app.add_exception_handler(DomainError, domain_error_handler)
app.add_exception_handler(SQLAlchemyError, db_error_handler)

app.include_router(transactions.router, prefix="/api")
app.include_router(accounts.router, prefix="/api")
app.include_router(stats.router, prefix="/api")


@app.get("/api/health", tags=["health"])
def health():
    with get_engine().connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok", "model": app.state.model.name, "threshold": app.state.model.threshold}
