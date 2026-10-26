from fastapi import APIRouter, Depends
from sqlalchemy import Engine, text

from app.dependencies import engine_dep
from app.schemas.transaction import StatsOut

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=StatsOut)
def stats(engine: Engine = Depends(engine_dep)):
    """Admin dashboard headline numbers - one round trip, no scan of the 6M-row ledger.

    * live numbers come from fraud_logs (1 row per API-scored transaction, so it stays small)
    * dataset numbers come from mv_fraud_summary (a few hundred pre-aggregated rows)
    * blocked accounts uses the partial index idx_accounts_blocked
    """
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT
              (SELECT COUNT(*) FROM fraud_logs)                                         AS evaluated,
              (SELECT COUNT(*) FROM fraud_logs
                WHERE logged_at >= date_trunc('day', now()))                            AS today,
              (SELECT COUNT(*) FROM fraud_logs WHERE risk_level = 'HIGH')               AS high,
              (SELECT COUNT(*) FROM fraud_logs WHERE risk_level = 'MEDIUM')             AS medium,
              (SELECT COUNT(*) FROM fraud_logs WHERE risk_level = 'LOW')                AS low,
              (SELECT COALESCE(SUM(txn_count), 0)::bigint   FROM mv_fraud_summary)      AS ds_txns,
              (SELECT COALESCE(SUM(fraud_count), 0)::bigint FROM mv_fraud_summary)      AS ds_fraud,
              (SELECT COUNT(*) FROM accounts WHERE status = 'BLOCKED')                  AS blocked
        """)).mappings().one()
    return {
        "total_transactions": row["ds_txns"] + row["evaluated"],
        "transactions_today": row["today"],
        "fraud_flagged": row["high"],
        "blocked_accounts": row["blocked"],
        "live": {k: row[k] for k in ("evaluated", "today", "high", "medium", "low")},
        "dataset": {"transactions": row["ds_txns"], "fraud": row["ds_fraud"]},
    }


@router.get("/summary")
def summary(engine: Engine = Depends(engine_dep)):
    """Dashboard numbers: live model decisions + historical dataset (from the materialized view)."""
    with engine.connect() as conn:
        live = conn.execute(text("""
            SELECT COUNT(*)                                  AS evaluated,
                   COUNT(*) FILTER (WHERE risk_level='HIGH')   AS high,
                   COUNT(*) FILTER (WHERE risk_level='MEDIUM') AS medium,
                   COUNT(*) FILTER (WHERE risk_level='LOW')    AS low
              FROM fraud_logs""")).mappings().one()
        blocked_accounts = conn.execute(text("SELECT COUNT(*) FROM accounts WHERE status='BLOCKED'")).scalar_one()
        by_type = conn.execute(text("""
            SELECT type_code, SUM(txn_count)::bigint AS txn_count, SUM(fraud_count)::bigint AS fraud_count,
                   ROUND(100.0 * SUM(fraud_count) / NULLIF(SUM(txn_count), 0), 4) AS fraud_rate_pct
              FROM mv_fraud_summary GROUP BY type_code ORDER BY type_code""")).mappings().all()
        by_hour = conn.execute(text("""
            SELECT hour_of_day, SUM(txn_count)::bigint AS txn_count, SUM(fraud_count)::bigint AS fraud_count
              FROM mv_fraud_summary GROUP BY hour_of_day ORDER BY hour_of_day""")).mappings().all()
    return {"live": dict(live), "blocked_accounts": blocked_accounts,
            "dataset_by_type": [dict(r) for r in by_type],
            "dataset_by_hour": [dict(r) for r in by_hour]}
