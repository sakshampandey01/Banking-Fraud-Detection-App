-- =====================================================================================
-- Database behaviour tests. Run with psql against a database where sql/01..04 were applied:
--
--   psql "$DB" -v ON_ERROR_STOP=1 -q -f tests/sql/test_database.sql
--
-- Everything happens inside one transaction that is ROLLED BACK at the end, so it leaves no data
-- behind. It drives sp_process_transaction with the same client-style CALL (five NULL placeholders
-- for the OUT arguments) that app/services/transaction_service.py sends. Any failure aborts with
-- "FAILED: <what>"; otherwise every check prints "PASS: ...".
-- =====================================================================================
\set QUIET on
\pset tuples_only on
\pset format unaligned
BEGIN;

CREATE FUNCTION pg_temp.ok(cond boolean, msg text) RETURNS text LANGUAGE plpgsql AS $$
BEGIN
    IF cond IS NOT TRUE THEN RAISE EXCEPTION 'FAILED: %', msg; END IF;
    RETURN 'PASS: ' || msg;
END $$;

-- calls the procedure and requires it to fail with the given SQLSTATE
CREATE FUNCTION pg_temp.expect_error(expected text, p_orig text, p_dest text, p_type text, p_amt numeric, p_prob numeric)
RETURNS text LANGUAGE plpgsql AS $$
DECLARE a bigint; b text; c text; d text; e text; before_count bigint; after_count bigint;
BEGIN
    SELECT count(*) INTO before_count FROM transactions;
    BEGIN
        CALL sp_process_transaction(p_orig, p_dest, p_type, p_amt, 5, p_prob, 'TEST', 0.908351, 0.5, a, b, c, d, e);
    EXCEPTION WHEN OTHERS THEN
        IF SQLSTATE <> expected THEN
            RAISE EXCEPTION 'FAILED: expected SQLSTATE % but got % (%)', expected, SQLSTATE, SQLERRM;
        END IF;
        SELECT count(*) INTO after_count FROM transactions;
        IF after_count <> before_count THEN
            RAISE EXCEPTION 'FAILED: % left a transaction row behind', expected;
        END IF;
        RETURN 'PASS: ' || expected || ' raised (' || SQLERRM || '), nothing written';
    END;
    RAISE EXCEPTION 'FAILED: expected SQLSTATE % but the call succeeded', expected;
END $$;

-- ---------------------------------------------------------------- reference data
SELECT pg_temp.ok((SELECT count(*) FROM transaction_types) = 5, 'five transaction types are seeded');
SELECT pg_temp.ok(
    (SELECT string_agg(type_code || '=' || type_enc, ',' ORDER BY type_enc) FROM transaction_types)
      = 'CASH_IN=0,CASH_OUT=1,DEBIT=2,PAYMENT=3,TRANSFER=4',
    'type_enc equals the notebook LabelEncoder order (alphabetical)');

-- ---------------------------------------------------------------- accounts
SELECT fn_open_account('C700000001', 10000.00) AS id \gset a1_
SELECT fn_open_account('C700000002',   500.00) AS id \gset a2_
SELECT fn_open_account('M700000001',     0.00) AS id \gset m1_
SELECT pg_temp.ok((SELECT user_type FROM users u JOIN accounts a USING (user_id) WHERE a.account_number = 'M700000001') = 'MERCHANT',
                  'M-numbers become MERCHANT users');
SELECT pg_temp.ok((SELECT user_type FROM users u JOIN accounts a USING (user_id) WHERE a.account_number = 'C700000001') = 'CUSTOMER',
                  'C-numbers become CUSTOMER users');
DO $$ BEGIN
    BEGIN PERFORM fn_open_account('C700000001', 1);
    EXCEPTION WHEN SQLSTATE 'FD006' THEN RETURN; END;
    RAISE EXCEPTION 'FAILED: duplicate account should raise FD006';
END $$;
SELECT 'PASS: duplicate account raises FD006';
DO $$ BEGIN
    BEGIN INSERT INTO accounts (user_id, account_number) SELECT user_id, 'X123' FROM users LIMIT 1;
    EXCEPTION WHEN check_violation THEN RETURN; END;
    RAISE EXCEPTION 'FAILED: bad account number pattern must be rejected';
END $$;
SELECT 'PASS: account_number pattern is enforced by the database';

-- ---------------------------------------------------------------- LOW risk: money moves
CALL sp_process_transaction('C700000001', 'C700000002', 'TRANSFER', 1000.00, 5, 0.010000, 'TEST', 0.908351, 0.5, NULL, NULL, NULL, NULL, NULL) \gset low_
SELECT pg_temp.ok(:'low_o_txn_status' = 'COMPLETED' AND :'low_o_risk_level' = 'LOW' AND :'low_o_action' = 'APPROVED' AND :'low_o_orig_status' = 'ACTIVE',
                  'LOW: COMPLETED / APPROVED, origin stays ACTIVE');
SELECT pg_temp.ok((SELECT balance FROM accounts WHERE account_number = 'C700000001') = 9000.00
              AND (SELECT balance FROM accounts WHERE account_number = 'C700000002') = 1500.00,
                  'LOW: TRANSFER moved 1000.00 from origin to destination');
SELECT pg_temp.ok((SELECT old_balance_orig = 10000 AND new_balance_orig = 9000 AND old_balance_dest = 500 AND new_balance_dest = 1500
                     FROM transactions WHERE txn_id = :low_o_txn_id), 'LOW: ledger row stores old/new balances');
SELECT pg_temp.ok((SELECT source = 'API' AND is_fraud_label IS NULL FROM transactions WHERE txn_id = :low_o_txn_id), 'API rows are source=API with no dataset label');
SELECT pg_temp.ok((SELECT fraud_probability = 0.010000 AND risk_level = 'LOW' AND model_name = 'TEST' AND decision_threshold = 0.908351
                     FROM fraud_logs WHERE txn_id = :low_o_txn_id), 'LOW: fraud_logs records probability, level, model and threshold');
SELECT pg_temp.ok((SELECT count(*) FROM account_audit) = 0, 'LOW: no audit row (status unchanged)');

-- ---------------------------------------------------------------- MEDIUM: approved but flagged
CALL sp_process_transaction('C700000001', 'C700000002', 'CASH_OUT', 500.00, 6, 0.600000, 'TEST', 0.908351, 0.5, NULL, NULL, NULL, NULL, NULL) \gset med_
SELECT pg_temp.ok(:'med_o_txn_status' = 'COMPLETED' AND :'med_o_risk_level' = 'MEDIUM' AND :'med_o_action' = 'APPROVED_FLAGGED',
                  'MEDIUM: COMPLETED / APPROVED_FLAGGED');
SELECT pg_temp.ok((SELECT balance FROM accounts WHERE account_number = 'C700000001') = 8500.00, 'MEDIUM: money moved');

-- ---------------------------------------------------------------- boundary: p == threshold is HIGH, p == medium is MEDIUM
CALL sp_process_transaction('C700000001', 'C700000002', 'DEBIT', 1.00, 7, 0.500000, 'TEST', 0.908351, 0.5, NULL, NULL, NULL, NULL, NULL) \gset edge1_
SELECT pg_temp.ok(:'edge1_o_risk_level' = 'MEDIUM', 'p == medium threshold is MEDIUM (>=)');

-- ---------------------------------------------------------------- merchant destination
CALL sp_process_transaction('C700000001', 'M700000001', 'PAYMENT', 100.00, 8, 0.020000, 'TEST', 0.908351, 0.5, NULL, NULL, NULL, NULL, NULL) \gset pay_
SELECT pg_temp.ok((SELECT balance FROM accounts WHERE account_number = 'M700000001') = 0
              AND (SELECT balance FROM accounts WHERE account_number = 'C700000001') = 8399.00,
                  'PAYMENT to a merchant: origin debited, merchant balance untouched (not tracked)');
SELECT pg_temp.ok((SELECT old_balance_dest = 0 AND new_balance_dest = 0 FROM transactions WHERE txn_id = :pay_o_txn_id),
                  'PAYMENT: merchant old/new balance stay 0 like the dataset');

-- ---------------------------------------------------------------- CASH_IN moves the other way
CALL sp_process_transaction('C700000001', 'C700000002', 'CASH_IN', 200.00, 9, 0.010000, 'TEST', 0.908351, 0.5, NULL, NULL, NULL, NULL, NULL) \gset cin_
SELECT pg_temp.ok((SELECT balance FROM accounts WHERE account_number = 'C700000001') = 8599.00
              AND (SELECT balance FROM accounts WHERE account_number = 'C700000002') = 1801.00,
                  'CASH_IN: origin up, counterparty down');

-- ---------------------------------------------------------------- HIGH: blocked, no money, account blocked + audited
SELECT balance AS orig_before FROM accounts WHERE account_number = 'C700000002' \gset
CALL sp_process_transaction('C700000002', 'C700000001', 'TRANSFER', 300.00, 10, 0.950000, 'TEST', 0.908351, 0.5, NULL, NULL, NULL, NULL, NULL) \gset high_
SELECT pg_temp.ok(:'high_o_txn_status' = 'BLOCKED' AND :'high_o_risk_level' = 'HIGH' AND :'high_o_action' = 'BLOCKED' AND :'high_o_orig_status' = 'BLOCKED',
                  'HIGH: transaction BLOCKED and origin account BLOCKED');
SELECT pg_temp.ok((SELECT balance FROM accounts WHERE account_number = 'C700000002') = :orig_before
              AND (SELECT balance FROM accounts WHERE account_number = 'C700000001') = 8599.00,
                  'HIGH: no money moved');
SELECT pg_temp.ok((SELECT old_balance_orig = new_balance_orig AND old_balance_dest = new_balance_dest AND status = 'BLOCKED'
                     FROM transactions WHERE txn_id = :high_o_txn_id), 'HIGH: ledger row has old == new balances');
SELECT pg_temp.ok((SELECT count(*) = 1 AND bool_and(old_status = 'ACTIVE' AND new_status = 'BLOCKED' AND reason LIKE 'AUTO: HIGH-risk transaction %' AND changed_by = current_user::text)
                     FROM account_audit au JOIN accounts a USING (account_id) WHERE a.account_number = 'C700000002'),
                  'HIGH: audit trigger recorded ACTIVE->BLOCKED with the automatic reason');

-- ---------------------------------------------------------------- business-rule errors (each must write nothing)
SELECT pg_temp.expect_error('FD002', 'C700000002', 'C700000001', 'TRANSFER', 1, 0.01);   -- origin now blocked
SELECT pg_temp.expect_error('FD001', 'C799999999', 'C700000001', 'TRANSFER', 1, 0.01);   -- unknown origin
SELECT pg_temp.expect_error('FD001', 'C700000001', 'C799999999', 'TRANSFER', 1, 0.01);   -- unknown destination
SELECT pg_temp.expect_error('FD003', 'C700000001', 'C700000002', 'TRANSFER', 999999, 0.01);   -- not enough funds
SELECT pg_temp.expect_error('FD003', 'C700000001', 'C700000002', 'CASH_IN', 999999, 0.01);    -- counterparty cannot fund it
SELECT pg_temp.expect_error('FD004', 'C700000001', 'C700000002', 'BOGUS', 1, 0.01);
SELECT pg_temp.expect_error('FD005', 'C700000001', 'C700000001', 'TRANSFER', 1, 0.01);
SELECT pg_temp.expect_error('22023', 'C700000001', 'C700000002', 'TRANSFER', 0, 0.01);       -- amount must be > 0
SELECT pg_temp.expect_error('22023', 'C700000001', 'C700000002', 'TRANSFER', 1, 1.5);        -- probability out of range

-- ---------------------------------------------------------------- manual unblock is audited with the router's mechanism
SELECT set_config('app.change_reason', 'MANUAL: analyst review', true) \gset
UPDATE accounts SET status = 'ACTIVE' WHERE account_number = 'C700000002';
SELECT pg_temp.ok((SELECT reason = 'MANUAL: analyst review' AND old_status = 'BLOCKED' AND new_status = 'ACTIVE'
                     FROM account_audit au JOIN accounts a USING (account_id)
                    WHERE a.account_number = 'C700000002' ORDER BY au.audit_id DESC LIMIT 1), 'manual status change is audited with its reason');
UPDATE accounts SET status = 'ACTIVE' WHERE account_number = 'C700000002';     -- no change -> no new audit row
SELECT pg_temp.ok((SELECT count(*) FROM account_audit au JOIN accounts a USING (account_id) WHERE a.account_number = 'C700000002') = 2,
                  'an UPDATE that does not change the status writes no audit row');

-- ---------------------------------------------------------------- constraints
DO $$ BEGIN
    BEGIN UPDATE accounts SET balance = -1 WHERE account_number = 'C700000001';
    EXCEPTION WHEN check_violation THEN RETURN; END;
    RAISE EXCEPTION 'FAILED: negative balance must be impossible';
END $$;
SELECT 'PASS: negative balances are rejected by a CHECK constraint';

-- ---------------------------------------------------------------- view contract with TransactionOut
SELECT pg_temp.ok(
    (SELECT array_agg(column_name::text ORDER BY column_name) FROM information_schema.columns WHERE table_name = 'v_transaction_details')
    @> ARRAY['action_taken','amount','created_at','dest_account','fraud_probability','is_fraud_label','model_name','new_balance_dest',
             'new_balance_orig','old_balance_dest','old_balance_orig','orig_account','orig_account_status','risk_level','source',
             'status','step','txn_id','type_code'],
    'v_transaction_details exposes every TransactionOut column');
SELECT pg_temp.ok((SELECT pg_typeof(fraud_probability)::text FROM v_transaction_details LIMIT 1) = 'double precision', 'view returns fraud_probability as float');

-- the exact filters used by GET /api/transactions
SELECT pg_temp.ok((SELECT count(*) FROM v_transaction_details WHERE source = 'API' AND risk_level = 'HIGH' AND status = 'BLOCKED' AND orig_account = 'C700000002') = 1,
                  'list filters source/status/risk_level/orig_account work on the view');

-- GET /api/transactions/{account}: both sides through the CTE used by the router
SELECT pg_temp.ok((
  WITH acct AS (SELECT account_id FROM accounts WHERE account_number = 'C700000002'),
  mine AS (
      SELECT t.txn_id FROM transactions t JOIN acct ON t.orig_account_id = acct.account_id
      UNION
      SELECT t.txn_id FROM transactions t JOIN acct ON t.dest_account_id = acct.account_id)
  SELECT count(*) FILTER (WHERE v.orig_account = 'C700000002') = 1 AND count(*) FILTER (WHERE v.orig_account <> 'C700000002') >= 3
    FROM v_transaction_details v JOIN mine USING (txn_id)), 'account history returns sent and received transactions');

-- ---------------------------------------------------------------- stats (the exact query of GET /api/stats)
INSERT INTO transactions (step, type_code, amount, orig_account_id, dest_account_id, old_balance_orig, new_balance_orig,
                          old_balance_dest, new_balance_dest, status, source, is_fraud_label)
SELECT 25, 'TRANSFER', 10, o.account_id, d.account_id, 10, 0, 0, 10, 'COMPLETED', 'DATASET', true
  FROM accounts o, accounts d WHERE o.account_number = 'C700000001' AND d.account_number = 'C700000002';
INSERT INTO transactions (step, type_code, amount, orig_account_id, dest_account_id, old_balance_orig, new_balance_orig,
                          old_balance_dest, new_balance_dest, status, source, is_fraud_label)
SELECT 49, 'TRANSFER', 20, o.account_id, d.account_id, 20, 20, 0, 0, 'COMPLETED', 'DATASET', false
  FROM accounts o, accounts d WHERE o.account_number = 'C700000001' AND d.account_number = 'C700000002';
REFRESH MATERIALIZED VIEW mv_fraud_summary;
SELECT pg_temp.ok((SELECT txn_count = 2 AND fraud_count = 1 FROM mv_fraud_summary WHERE type_code = 'TRANSFER' AND hour_of_day = 1),
                  'mv_fraud_summary groups DATASET rows by type and step % 24 (steps 25 and 49 -> hour 1)');
SELECT pg_temp.ok((SELECT count(*) FROM mv_fraud_summary WHERE type_code <> 'TRANSFER' OR hour_of_day <> 1) = 0,
                  'mv_fraud_summary ignores API rows');
SELECT pg_temp.ok((
  SELECT (SELECT COUNT(*) FROM fraud_logs) = 6 AND (SELECT COUNT(*) FROM fraud_logs WHERE risk_level = 'HIGH') = 1
     AND (SELECT COUNT(*) FROM fraud_logs WHERE risk_level = 'MEDIUM') = 2
     AND (SELECT COUNT(*) FROM fraud_logs WHERE risk_level = 'LOW') = 3
     AND (SELECT COALESCE(SUM(txn_count), 0)::bigint FROM mv_fraud_summary) = 2
     AND (SELECT COALESCE(SUM(fraud_count), 0)::bigint FROM mv_fraud_summary) = 1
     AND (SELECT COUNT(*) FROM accounts WHERE status = 'BLOCKED') = 0
     AND (SELECT COUNT(*) FROM fraud_logs WHERE logged_at >= date_trunc('day', now())) = 6),
  'stats query: live HIGH/MEDIUM/LOW, dataset totals, blocked accounts and today counts');
SELECT pg_temp.ok((SELECT round(100.0 * SUM(fraud_count) / NULLIF(SUM(txn_count), 0), 4) FROM mv_fraud_summary) = 50.0000, 'summary fraud rate arithmetic');

ROLLBACK;
SELECT 'ALL DATABASE TESTS PASSED (transaction rolled back, no data left behind)';
