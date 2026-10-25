"""
Business flow for POST /api/transactions/evaluate

  1. read-only lookup (accounts exist? origin blocked? dest is merchant? type rules)
  2. build features -> ML probability                (NO database transaction open)
  3. CALL sp_process_transaction(...)                (one atomic DB transaction)
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from app.errors import DomainError, translate_db_error
from app.ml.features import FeatureBuilder
from app.ml.model_service import FraudModel
from app.schemas.transaction import EvaluateRequest, EvaluateResponse

MESSAGES = {
    "LOW": "Transaction approved.",
    "MEDIUM": "Transaction approved but flagged for monitoring.",
    "HIGH": "Transaction blocked as suspected fraud; the originating account has been blocked.",
}


def _default_step(now: datetime | None = None) -> int:
    """PaySim 'step' = hour within a 30-day window. Derive it from the wall clock."""
    now = now or datetime.now()
    return min(24 * (now.day - 1) + now.hour + 1, 743)


def _as_numeric(value: float) -> Decimal:
    return Decimal(str(round(value, 6)))             # matches NUMERIC(7,6)


def evaluate_transaction(engine: Engine, model: FraudModel, builder: FeatureBuilder,
                         medium_threshold: float, req: EvaluateRequest) -> EvaluateResponse:
    # ---- 1. lookups ---------------------------------------------------------
    with engine.connect() as conn:
        accounts = {
            r.account_number: r
            for r in conn.execute(
                text("""SELECT a.account_number, a.status, a.balance, u.user_type
                          FROM accounts a JOIN users u USING (user_id)
                         WHERE a.account_number IN (:o, :d)"""),
                {"o": req.orig_account, "d": req.dest_account},
            )
        }
        rule = conn.execute(
            text("SELECT origin_effect, dest_effect FROM transaction_types WHERE type_code = :t"),
            {"t": req.type},
        ).one_or_none()

    for number in (req.orig_account, req.dest_account):
        if number not in accounts:
            raise DomainError(404, "ACCOUNT_NOT_FOUND", f"Account {number} does not exist")
    if req.orig_account == req.dest_account:
        raise DomainError(422, "SAME_ACCOUNT", "Origin and destination are identical")
    if rule is None:
        raise DomainError(400, "UNKNOWN_TYPE", f"Unknown transaction type {req.type}")
    if accounts[req.orig_account].status != "ACTIVE":        # fast-fail; the procedure re-checks under lock
        raise DomainError(423, "ACCOUNT_BLOCKED", f"Account {req.orig_account} is blocked")

    # Fast-fail only (saves an ML call and gives the user a clear message). NOT authoritative:
    # the stored procedure re-checks under a row lock, so concurrent requests cannot overdraw.
    if rule.origin_effect == -1 and accounts[req.orig_account].balance < req.amount:
        raise DomainError(422, "INSUFFICIENT_FUNDS",
                          f"Insufficient funds: balance {accounts[req.orig_account].balance}, "
                          f"requested {req.amount}")

    # ---- 2. features + prediction ---------------------------------------------
    amount = float(req.amount)
    dest_is_merchant = accounts[req.dest_account].user_type == "MERCHANT"
    step = req.step or _default_step()
    features = builder.build(
        type_code=req.type,
        amount=amount,
        step=step,
        balance_diff_orig=-rule.origin_effect * amount,                     # old - new
        balance_diff_dest=0.0 if dest_is_merchant else rule.dest_effect * amount,   # new - old
    )
    probability = _as_numeric(model.predict_proba(features))

    # ---- 3. stored procedure ---------------------------------------------------
    try:
        with engine.begin() as conn:                       # commit on success, rollback on error
            row = conn.execute(
                text("""CALL sp_process_transaction(
                            :orig, :dest, :type, :amount, :step,
                            :prob, :model_name, :threshold, :medium,
                            NULL, NULL, NULL, NULL, NULL)"""),
                {
                    "orig": req.orig_account, "dest": req.dest_account, "type": req.type,
                    "amount": req.amount, "step": step,
                    "prob": probability, "model_name": model.name,
                    "threshold": _as_numeric(model.threshold),
                    "medium": _as_numeric(medium_threshold),
                },
            ).mappings().one()
    except DBAPIError as exc:
        domain = translate_db_error(exc)
        if domain:
            raise domain from exc
        raise

    return EvaluateResponse(
        txn_id=row["o_txn_id"],
        status=row["o_txn_status"],
        risk_level=row["o_risk_level"],
        action_taken=row["o_action"],
        is_fraud=row["o_risk_level"] == "HIGH",
        fraud_probability=float(probability),
        decision_threshold=round(model.threshold, 6),
        model_name=model.name,
        origin_account_status=row["o_orig_status"],
        message=MESSAGES[row["o_risk_level"]],
    )
