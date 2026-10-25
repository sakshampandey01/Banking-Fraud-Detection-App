"""FastAPI dependencies: hand the objects created at startup to the route handlers."""
from fastapi import Request
from sqlalchemy import Engine

from app.database import get_engine
from app.ml.features import FeatureBuilder
from app.ml.model_service import FraudModel


def engine_dep() -> Engine:
    return get_engine()


def model_dep(request: Request) -> FraudModel:
    return request.app.state.model


def builder_dep(request: Request) -> FeatureBuilder:
    return request.app.state.builder
