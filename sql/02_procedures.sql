-- =====================================================================
-- 02_procedures.sql  --  sp_process_transaction
-- Single DB-side entry point for a live transaction. In ONE atomic unit:
--   1. validates type / accounts / status
--   2. locks both accounts (consistent order => no deadlocks)
--   3. classifies risk from the ML probability  (business rule lives in DB)
--   4. moves money ONLY if the transaction is not HIGH risk
--   5. inserts the transaction + the fraud_log row
--      (the fraud_logs trigger then auto-blocks the origin account)
--
-- Custom error codes (SQLSTATE) mapped to HTTP errors by the API:
--   FD001 account not found     FD002 account blocked
--   FD003 insufficient funds    FD004 unknown transaction type
--   FD005 origin = destination
-- =====================================================================
CREATE OR REPLACE PROCEDURE sp_process_transaction(
    p_orig_account      VARCHAR,
    p_dest_account      VARCHAR,
    p_type_code         VARCHAR,
    p_amount            NUMERIC,
    p_step              INTEGER,
    p_fraud_probability NUMERIC,   -- from the ML model, 0..1
    p_model_name        VARCHAR,
    p_model_threshold   NUMERIC,   -- probability >= this  => HIGH
    p_medium_threshold  NUMERIC,   -- probability >= this  => MEDIUM
    INOUT o_txn_id      BIGINT  DEFAULT NULL,
    INOUT o_txn_status  VARCHAR DEFAULT NULL,
    INOUT o_risk_level  VARCHAR DEFAULT NULL,
    INOUT o_action      VARCHAR DEFAULT NULL,
    INOUT o_orig_status VARCHAR DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_type             transaction_types%ROWTYPE;
    v_orig_id          BIGINT;
    v_dest_id          BIGINT;
    v_orig             accounts%ROWTYPE;
    v_dest             accounts%ROWTYPE;
    v_dest_is_merchant BOOLEAN;
    v_orig_delta       NUMERIC := 0;
    v_dest_delta       NUMERIC := 0;
    v_move_money       BOOLEAN;
BEGIN
    -- 1. validation ----------------------------------------------------
    SELECT * INTO v_type FROM transaction_types WHERE type_code = p_type_code;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'UNKNOWN_TYPE: %', p_type_code USING ERRCODE = 'FD004';
    END IF;

    SELECT account_id INTO v_orig_id FROM accounts WHERE account_number = p_orig_account;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'ACCOUNT_NOT_FOUND: %', p_orig_account USING ERRCODE = 'FD001';
    END IF;
    SELECT account_id INTO v_dest_id FROM accounts WHERE account_number = p_dest_account;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'ACCOUNT_NOT_FOUND: %', p_dest_account USING ERRCODE = 'FD001';
    END IF;
    IF v_orig_id = v_dest_id THEN
        RAISE EXCEPTION 'SAME_ACCOUNT: origin and destination are identical' USING ERRCODE = 'FD005';
    END IF;

    -- 2. lock both rows in id order, then re-read the fresh values -------
    PERFORM 1 FROM accounts
     WHERE account_id IN (v_orig_id, v_dest_id)
     ORDER BY account_id
       FOR UPDATE;
    SELECT * INTO v_orig FROM accounts WHERE account_id = v_orig_id;
    SELECT * INTO v_dest FROM accounts WHERE account_id = v_dest_id;

    IF v_orig.status <> 'ACTIVE' THEN
        RAISE EXCEPTION 'ACCOUNT_BLOCKED: %', p_orig_account USING ERRCODE = 'FD002';
    END IF;

    -- 3. risk classification (thresholds are passed in, rule is applied here)
    o_risk_level := CASE
                        WHEN p_fraud_probability >= p_model_threshold  THEN 'HIGH'
                        WHEN p_fraud_probability >= p_medium_threshold THEN 'MEDIUM'
                        ELSE 'LOW'
                    END;
    v_move_money := (o_risk_level <> 'HIGH');

    -- 4. balance movement (rules come from transaction_types) -------------
    SELECT (user_type = 'MERCHANT') INTO v_dest_is_merchant
      FROM users WHERE user_id = v_dest.user_id;

    v_orig_delta := v_type.origin_effect * p_amount;
    -- merchant balances are not tracked in the dataset => no change
    v_dest_delta := CASE WHEN v_dest_is_merchant THEN 0
                         ELSE v_type.dest_effect * p_amount END;

    IF v_move_money THEN
        IF v_orig.balance + v_orig_delta < 0 THEN
            RAISE EXCEPTION 'INSUFFICIENT_FUNDS: account % has % but needs %',
                            p_orig_account, v_orig.balance, p_amount USING ERRCODE = 'FD003';
        END IF;
        IF v_dest.balance + v_dest_delta < 0 THEN
            RAISE EXCEPTION 'INSUFFICIENT_FUNDS: destination % cannot cover this movement',
                            p_dest_account USING ERRCODE = 'FD003';
        END IF;
        UPDATE accounts SET balance = balance + v_orig_delta WHERE account_id = v_orig_id;
        UPDATE accounts SET balance = balance + v_dest_delta WHERE account_id = v_dest_id;
    ELSE
        v_orig_delta := 0;       -- blocked: funds stay where they are
        v_dest_delta := 0;
    END IF;

    o_txn_status := CASE WHEN v_move_money THEN 'COMPLETED' ELSE 'BLOCKED' END;
    o_action     := CASE o_risk_level WHEN 'HIGH'   THEN 'BLOCKED'
                                      WHEN 'MEDIUM' THEN 'APPROVED_FLAGGED'
                                      ELSE 'APPROVED' END;

    -- 5. persist -----------------------------------------------------------
    INSERT INTO transactions (step, type_code, amount, orig_account_id, dest_account_id,
                              old_balance_orig, new_balance_orig,
                              old_balance_dest, new_balance_dest,
                              status, source)
    VALUES (p_step, p_type_code, p_amount, v_orig_id, v_dest_id,
            v_orig.balance, v_orig.balance + v_orig_delta,
            v_dest.balance, v_dest.balance + v_dest_delta,
            o_txn_status, 'API')
    RETURNING txn_id INTO o_txn_id;

    -- the AFTER INSERT trigger on fraud_logs blocks the account when HIGH
    INSERT INTO fraud_logs (txn_id, fraud_probability, risk_level, action_taken,
                            model_name, model_threshold)
    VALUES (o_txn_id, p_fraud_probability, o_risk_level, o_action,
            p_model_name, p_model_threshold);

    SELECT status INTO o_orig_status FROM accounts WHERE account_id = v_orig_id;
END;
$$;
