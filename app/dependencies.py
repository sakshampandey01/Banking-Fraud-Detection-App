"""FastAPI dependencies: hand the objects created at startup to the route handlers."""
from fastapi import Request
from sqlalchemy import Engine

from app.database import get_engine
from app.runtime import Runtime


def engine_dep() -> Engine:
    return get_engine()


def runtime_dep(request: Request) -> Runtime:
    return request.app.state.runtime
