-- DANGER: removes every table, view and routine of this project, and ALL data in them.
-- Only run through:  python scripts/init_db.py --reset --yes
DROP MATERIALIZED VIEW IF EXISTS mv_fraud_summary;
DROP VIEW      IF EXISTS v_transaction_details;
DROP PROCEDURE IF EXISTS sp_process_transaction(TEXT, TEXT, TEXT, NUMERIC, INTEGER, NUMERIC, TEXT, NUMERIC, NUMERIC);
DROP FUNCTION  IF EXISTS fn_open_account(TEXT, NUMERIC);
DROP TABLE     IF EXISTS account_audit, fraud_logs, transactions, transaction_types, accounts, users CASCADE;
DROP FUNCTION  IF EXISTS fn_audit_account_status();
