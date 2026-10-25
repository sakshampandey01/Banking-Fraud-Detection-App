from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import Engine, text

from app.config import get_settings
from app.dependencies import builder_dep, engine_dep, model_dep
from app.ml.features import FeatureBuilder
from app.ml.model_service import FraudModel
from app.schemas.transaction import (ACCOUNT_PATTERN, AccountTransactionOut, EvaluateRequest,
                                     EvaluateResponse, TransactionOut)
from app.services.transaction_service import evaluate_transaction

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("/evaluate", response_model=EvaluateResponse, status_code=201)
def evaluate(
    payload: EvaluateRequest,
    engine: Engine = Depends(engine_dep),
    model: FraudModel = Depends(model_dep),
    builder: FeatureBuilder = Depends(builder_dep),
):
    """Score a transaction with the ML model, then persist it via the stored procedure."""
    return evaluate_transaction(engine, model, builder, get_settings().medium_risk_threshold, payload)


@router.get("", response_model=list[TransactionOut])
def list_transactions(
    engine: Engine = Depends(engine_dep),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    source: Optional[Literal["API", "DATASET"]] = None,
    status: Optional[Literal["COMPLETED", "BLOCKED"]] = None,
    risk_level: Optional[Literal["LOW", "MEDIUM", "HIGH"]] = None,
    account: Optional[str] = Query(None, description="origin account number"),
):
    """Newest first. Filters are optional and combined with AND."""
    clauses, params = [], {"limit": limit, "offset": offset}
    for column, value in (("source", source), ("status", status),
                          ("risk_level", risk_level), ("orig_account", account)):
        if value is not None:
            clauses.append(f"{column} = :{column}")      # column names come from the tuple above, never from the user
            params[column] = value
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    with engine.connect() as conn:
        rows = conn.execute(
            text(f"SELECT * FROM v_transaction_details {where} ORDER BY txn_id DESC LIMIT :limit OFFSET :offset"),
            params,
        ).mappings().all()
    return rows


# Resolve the account id once, then read each side through its own index
# (idx_txn_orig_step / idx_txn_dest). A single "orig = :n OR dest = :n" over the view
# would force a scan of the whole ledger.
_ACCOUNT_TXNS_SQL = """
WITH acct AS (SELECT account_id FROM accounts WHERE account_number = :n),
mine AS (
    SELECT t.txn_id FROM transactions t JOIN acct ON t.orig_account_id = acct.account_id
    UNION
    SELECT t.txn_id FROM transactions t JOIN acct ON t.dest_account_id = acct.account_id
)
SELECT v.*,
       CASE WHEN v.orig_account = :n THEN 'SENT' ELSE 'RECEIVED' END AS direction
  FROM v_transaction_details v
  JOIN mine USING (txn_id)
 ORDER BY v.created_at DESC, v.txn_id DESC
 LIMIT :limit OFFSET :offset
"""


@router.get("/{txn_id:int}", response_model=TransactionOut)
def get_transaction(txn_id: int, engine: Engine = Depends(engine_dep)):
    with engine.connect() as conn:
        row = conn.execute(text("SELECT * FROM v_transaction_details WHERE txn_id = :i"),
                           {"i": txn_id}).mappings().one_or_none()
    if row is None:
        raise HTTPException(404, "Transaction not found")
    return row


# Declared AFTER "/{txn_id:int}" (digits only), so /transactions/42 is a txn id and
# /transactions/C123... falls through to this account route.
@router.get("/{account_number}", response_model=list[AccountTransactionOut])
def account_transactions(
    account_number: str = Path(pattern=ACCOUNT_PATTERN),
    engine: Engine = Depends(engine_dep),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Every transaction where this account was source OR destination, newest first."""
    with engine.connect() as conn:
        exists = conn.execute(text("SELECT 1 FROM accounts WHERE account_number = :n"),
                              {"n": account_number}).scalar_one_or_none()
        if exists is None:
            raise HTTPException(404, "Account not found")
        return conn.execute(text(_ACCOUNT_TXNS_SQL),
                            {"n": account_number, "limit": limit, "offset": offset}).mappings().all()
