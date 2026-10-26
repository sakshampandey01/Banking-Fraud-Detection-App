-- =====================================================================================
-- Routines: audit trigger, account opening, and the atomic transaction procedure.
-- Requires PostgreSQL 14+ (procedures with OUT parameters). Safe to run repeatedly.
--
-- Custom error codes raised here are translated to HTTP errors in app/errors.py:
--   FD001 account not found      FD002 origin account blocked    FD003 insufficient funds
--   FD004 unknown type           FD005 same account              FD006 account already exists
-- =====================================================================================

-- ---- audit: every change of accounts.status is recorded ------------------------------
-- The reason is passed from the caller with  SELECT set_config('app.change_reason', '...', true)
-- (transaction-local). changed_by defaults to the database user.
CREATE OR REPLACE FUNCTION fn_audit_account_status() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO account_audit (account_id, old_status, new_status, reason, changed_by)
    VALUES (NEW.account_id, OLD.status, NEW.status,
            COALESCE(NULLIF(current_setting('app.change_reason', true), ''), 'UNSPECIFIED'),
            COALESCE(NULLIF(current_setting('app.changed_by',    true), ''), current_user::text));
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_accounts_status_audit ON accounts;
CREATE TRIGGER trg_accounts_status_audit
    AFTER UPDATE OF status ON accounts
    FOR EACH ROW
    WHEN (OLD.status IS DISTINCT FROM NEW.status)
    EXECUTE FUNCTION fn_audit_account_status();


-- ---- open an account (user + account in one atomic call) ------------------------------
-- 'M...' numbers are merchants, everything else customers. Returns the new account_id.
CREATE OR REPLACE FUNCTION fn_open_account(p_account_number TEXT, p_balance NUMERIC DEFAULT 0)
RETURNS BIGINT
LANGUAGE plpgsql AS $$
DECLARE
    v_user_id    BIGINT;
    v_account_id BIGINT;
BEGIN
    IF EXISTS (SELECT 1 FROM accounts WHERE account_number = p_account_number) THEN
        RAISE EXCEPTION 'Account % already exists', p_account_number USING ERRCODE = 'FD006';
    END IF;
    INSERT INTO users (user_type)
    VALUES (CASE WHEN left(p_account_number, 1) = 'M' THEN 'MERCHANT' ELSE 'CUSTOMER' END)
    RETURNING user_id INTO v_user_id;
    INSERT INTO accounts (user_id, account_number, balance)
    VALUES (v_user_id, p_account_number, p_balance)
    RETURNING account_id INTO v_account_id;
    RETURN v_account_id;
END;
$$;


-- ---- sp_process_transaction ----------------------------------------------------------------
-- Called by app/services/transaction_service.py AFTER the model has produced p_prob:
--   CALL sp_process_transaction(orig, dest, type, amount, step, prob, model_name, threshold, medium,
--                               NULL, NULL, NULL, NULL, NULL);
-- In one database transaction it: locks both accounts, re-checks the business rules, classifies the
-- risk (HIGH if p >= threshold, MEDIUM if p >= medium, else LOW), then
--   LOW / MEDIUM -> moves the balances and records the transaction as COMPLETED
--   HIGH         -> records it as BLOCKED, moves NO money and blocks the origin account (audited)
-- and writes the model's verdict to fraud_logs. Merchant destinations keep their balance (not tracked).
CREATE OR REPLACE PROCEDURE sp_process_transaction(
    p_orig        TEXT,
    p_dest        TEXT,
    p_type        TEXT,
    p_amount      NUMERIC,
    p_step        INTEGER,
    p_prob        NUMERIC,
    p_model_name  TEXT,
    p_threshold   NUMERIC,
    p_medium      NUMERIC,
    OUT o_txn_id       BIGINT,
    OUT o_txn_status   TEXT,
    OUT o_risk_level   TEXT,
    OUT o_action       TEXT,
    OUT o_orig_status  TEXT
)
LANGUAGE plpgsql AS $$
DECLARE
    v_rule             transaction_types%ROWTYPE;
    v_orig             accounts%ROWTYPE;
    v_dest             accounts%ROWTYPE;
    v_dest_is_merchant BOOLEAN;
    v_new_orig         NUMERIC(18,2);
    v_new_dest         NUMERIC(18,2);
BEGIN
    IF p_amount IS NULL OR p_amount <= 0 THEN
        RAISE EXCEPTION 'Amount must be greater than zero' USING ERRCODE = '22023';
    END IF;
    IF p_prob IS NULL OR p_prob < 0 OR p_prob > 1 THEN
        RAISE EXCEPTION 'Fraud probability must be between 0 and 1' USING ERRCODE = '22023';
    END IF;
    IF p_orig = p_dest THEN
        RAISE EXCEPTION 'Origin and destination are identical' USING ERRCODE = 'FD005';
    END IF;

    -- Lock both rows in a fixed order so two opposite transfers can never deadlock.
    PERFORM 1 FROM accounts WHERE account_number IN (p_orig, p_dest) ORDER BY account_id FOR UPDATE;

    SELECT * INTO v_orig FROM accounts WHERE account_number = p_orig;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Account % does not exist', p_orig USING ERRCODE = 'FD001';
    END IF;
    SELECT * INTO v_dest FROM accounts WHERE account_number = p_dest;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Account % does not exist', p_dest USING ERRCODE = 'FD001';
    END IF;

    SELECT * INTO v_rule FROM transaction_types WHERE type_code = p_type;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Unknown transaction type %', p_type USING ERRCODE = 'FD004';
    END IF;

    IF v_orig.status <> 'ACTIVE' THEN
        RAISE EXCEPTION 'Account % is blocked', p_orig USING ERRCODE = 'FD002';
    END IF;

    SELECT (u.user_type = 'MERCHANT') INTO v_dest_is_merchant FROM users u WHERE u.user_id = v_dest.user_id;

    IF v_rule.origin_effect = -1 AND v_orig.balance < p_amount THEN
        RAISE EXCEPTION 'Insufficient funds: balance %, requested %', v_orig.balance, p_amount USING ERRCODE = 'FD003';
    END IF;
    IF v_rule.dest_effect = -1 AND NOT v_dest_is_merchant AND v_dest.balance < p_amount THEN
        RAISE EXCEPTION 'Insufficient funds in destination account %: balance %, requested %',
                        p_dest, v_dest.balance, p_amount USING ERRCODE = 'FD003';
    END IF;

    -- ---- the model's verdict ----------------------------------------------------------------
    o_risk_level := CASE WHEN p_prob >= p_threshold THEN 'HIGH'
                         WHEN p_prob >= p_medium    THEN 'MEDIUM'
                         ELSE 'LOW' END;

    -- ---- money movement (none for a blocked transaction) -------------------------------------
    v_new_orig := v_orig.balance;
    v_new_dest := v_dest.balance;
    IF o_risk_level = 'HIGH' THEN
        o_txn_status := 'BLOCKED';
        o_action     := 'BLOCKED';
    ELSE
        o_txn_status := 'COMPLETED';
        o_action     := CASE o_risk_level WHEN 'MEDIUM' THEN 'APPROVED_FLAGGED' ELSE 'APPROVED' END;

        v_new_orig := v_orig.balance + v_rule.origin_effect * p_amount;
        UPDATE accounts SET balance = v_new_orig WHERE account_id = v_orig.account_id;

        IF NOT v_dest_is_merchant AND v_rule.dest_effect <> 0 THEN
            v_new_dest := v_dest.balance + v_rule.dest_effect * p_amount;
            UPDATE accounts SET balance = v_new_dest WHERE account_id = v_dest.account_id;
        END IF;
    END IF;

    INSERT INTO transactions (step, type_code, amount, orig_account_id, dest_account_id,
                              old_balance_orig, new_balance_orig, old_balance_dest, new_balance_dest,
                              status, source)
    VALUES (p_step, p_type, p_amount, v_orig.account_id, v_dest.account_id,
            v_orig.balance, v_new_orig, v_dest.balance, v_new_dest,
            o_txn_status, 'API')
    RETURNING txn_id INTO o_txn_id;

    INSERT INTO fraud_logs (txn_id, fraud_probability, risk_level, action_taken, model_name, decision_threshold)
    VALUES (o_txn_id, p_prob, o_risk_level, o_action, p_model_name, p_threshold);

    IF o_risk_level = 'HIGH' THEN
        PERFORM set_config('app.change_reason',
                           format('AUTO: HIGH-risk transaction %s (p=%s, threshold=%s)', o_txn_id, p_prob, p_threshold),
                           true);
        UPDATE accounts SET status = 'BLOCKED' WHERE account_id = v_orig.account_id;
    END IF;

    SELECT status INTO o_orig_status FROM accounts WHERE account_id = v_orig.account_id;
END;
$$;
