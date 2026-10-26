from fastapi import APIRouter, Depends

from app.config import get_settings
from app.dependencies import runtime_dep
from app.runtime import Runtime
from app.schemas.transaction import (BatchPredictRequest, BatchPredictResponse, PredictRequest,
                                     PredictResponse)
from app.services.transaction_service import predict_batch, predict_many

router = APIRouter(prefix="/predict", tags=["predict"])


@router.post("", response_model=PredictResponse)
def predict(payload: PredictRequest, runtime: Runtime = Depends(runtime_dep)):
    """Score one transaction with the saved model. Nothing is written to the database."""
    return predict_many(runtime, get_settings().medium_risk_threshold, [payload])[0]


@router.post("/batch", response_model=BatchPredictResponse)
def predict_batch_endpoint(payload: BatchPredictRequest, runtime: Runtime = Depends(runtime_dep)):
    """Score up to 1000 transactions in one request. Nothing is written to the database."""
    return predict_batch(runtime, get_settings().medium_risk_threshold, payload)
