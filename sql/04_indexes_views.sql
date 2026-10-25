-- =====================================================================
-- 04_indexes_views.sql  --  run AFTER the bulk load (faster that way)
-- =====================================================================

-- Indexes -------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_txn_orig_step    ON transactions (orig_account_id, step DESC);
CREATE INDEX IF NOT EXISTS idx_txn_dest         ON transactions (dest_account_id);
CREATE INDEX IF NOT EXISTS idx_txn_created_at   ON transactions (created_at DESC);
-- partial indexes: tiny, because fraud is rare (~0.13% of rows)
CREATE INDEX IF NOT EXISTS idx_txn_fraud_label  ON transactions (txn_id) WHERE is_fraud_label;
CREATE INDEX IF NOT EXISTS idx_txn_blocked      ON transactions (txn_id) WHERE status = 'BLOCKED';
CREATE INDEX IF NOT EXISTS idx_fraud_logs_high  ON fraud_logs (logged_at DESC) WHERE risk_level = 'HIGH';
CREATE INDEX IF NOT EXISTS idx_audit_account    ON account_audit (account_id, changed_at DESC);
CREATE INDEX IF NOT EXISTS idx_accounts_blocked ON accounts (account_id) WHERE status = 'BLOCKED';

-- Views ---------------------------------------------------------------
CREATE OR REPLACE VIEW v_transaction_details AS
SELECT t.txn_id, t.step, t.type_code, t.amount, t.status, t.source, t.created_at,
       t.is_fraud_label,
       ao.account_number AS orig_account,
       ad.account_number AS dest_account,
       ao.status         AS orig_account_status,
       t.old_balance_orig, t.new_balance_orig, t.old_balance_dest, t.new_balance_dest,
       f.fraud_probability, f.risk_level, f.action_taken, f.model_name
  FROM transactions t
  JOIN accounts ao ON ao.account_id = t.orig_account_id
  JOIN accounts ad ON ad.account_id = t.dest_account_id
  LEFT JOIN fraud_logs f ON f.txn_id = t.txn_id;

-- Materialized view: heavy aggregation over millions of rows, computed once.
-- Refresh with:  REFRESH MATERIALIZED VIEW CONCURRENTLY mv_fraud_summary;
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_fraud_summary AS
SELECT type_code,
       (step % 24)                                AS hour_of_day,
       COUNT(*)                                   AS txn_count,
       COUNT(*) FILTER (WHERE is_fraud_label)     AS fraud_count,
       SUM(amount)                                AS total_amount,
       SUM(amount) FILTER (WHERE is_fraud_label)  AS fraud_amount
  FROM transactions
 WHERE source = 'DATASET'
 GROUP BY type_code, (step % 24);

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_fraud_summary ON mv_fraud_summary (type_code, hour_of_day);
