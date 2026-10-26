-- =====================================================================================
-- Read models used by the API.   Safe to run repeatedly.
-- =====================================================================================

-- One row per transaction with both account numbers and the model's verdict (if any).
-- Column names match TransactionOut in app/schemas/transaction.py.
CREATE OR REPLACE VIEW v_transaction_details AS
SELECT t.txn_id,
       t.step,
       t.type_code,
       t.amount,
       t.status,
       t.source,
       t.created_at,
       ao.account_number                       AS orig_account,
       ad.account_number                       AS dest_account,
       ao.status                               AS orig_account_status,
       t.old_balance_orig,
       t.new_balance_orig,
       t.old_balance_dest,
       t.new_balance_dest,
       t.is_fraud_label,
       f.fraud_probability::double precision   AS fraud_probability,
       f.risk_level,
       f.action_taken,
       f.model_name
  FROM transactions t
  JOIN accounts   ao ON ao.account_id = t.orig_account_id
  JOIN accounts   ad ON ad.account_id = t.dest_account_id
  LEFT JOIN fraud_logs f ON f.txn_id = t.txn_id;

-- Pre-aggregated HISTORICAL dataset numbers (source = 'DATASET') so the dashboard never scans the
-- ledger. Refresh after importing data:  python scripts/init_db.py --refresh-summary
-- hour_of_day = step % 24, the same definition as the model's `hour` feature.
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_fraud_summary AS
SELECT type_code,
       (step % 24)                                       AS hour_of_day,
       COUNT(*)::bigint                                  AS txn_count,
       COUNT(*) FILTER (WHERE is_fraud_label)::bigint    AS fraud_count
  FROM transactions
 WHERE source = 'DATASET'
 GROUP BY type_code, (step % 24);

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_fraud_summary ON mv_fraud_summary (type_code, hour_of_day);
