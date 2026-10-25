-- =====================================================================
-- 03_triggers.sql
--   trg_block_account_on_high_risk : fraud_logs INSERT (HIGH) -> block origin account
--   trg_audit_account_status       : accounts.status change  -> account_audit row
--   trg_fraud_logs_append_only     : forbid UPDATE/DELETE on fraud_logs
-- The first two CASCADE: a HIGH-risk log fires trigger 1, whose UPDATE
-- fires trigger 2 -- all inside the caller's transaction.
-- =====================================================================

-- 1. auto-block ---------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_block_account_on_high_risk()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_account_id BIGINT;
BEGIN
    SELECT orig_account_id INTO v_account_id FROM transactions WHERE txn_id = NEW.txn_id;

    -- tell the audit trigger WHY (transaction-local setting)
    PERFORM set_config('app.change_reason',
                       format('AUTO_BLOCK: high-risk txn %s (p=%s)', NEW.txn_id, NEW.fraud_probability),
                       true);
    UPDATE accounts SET status = 'BLOCKED'
     WHERE account_id = v_account_id AND status <> 'BLOCKED';
    PERFORM set_config('app.change_reason', '', true);
    RETURN NULL;   -- AFTER trigger: return value ignored
END;
$$;

DROP TRIGGER IF EXISTS trg_block_account_on_high_risk ON fraud_logs;
CREATE TRIGGER trg_block_account_on_high_risk
    AFTER INSERT ON fraud_logs
    FOR EACH ROW
    WHEN (NEW.risk_level = 'HIGH')
    EXECUTE FUNCTION fn_block_account_on_high_risk();

-- 2. audit ----------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_audit_account_status()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO account_audit (account_id, old_status, new_status, reason)
    VALUES (NEW.account_id, OLD.status, NEW.status,
            COALESCE(NULLIF(current_setting('app.change_reason', true), ''), 'MANUAL'));
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_audit_account_status ON accounts;
CREATE TRIGGER trg_audit_account_status
    AFTER UPDATE OF status ON accounts
    FOR EACH ROW
    WHEN (OLD.status IS DISTINCT FROM NEW.status)
    EXECUTE FUNCTION fn_audit_account_status();

-- 3. append-only fraud log --------------------------------------------------
CREATE OR REPLACE FUNCTION fn_fraud_logs_append_only()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'fraud_logs is append-only (% not allowed)', TG_OP;
END;
$$;

DROP TRIGGER IF EXISTS trg_fraud_logs_append_only ON fraud_logs;
CREATE TRIGGER trg_fraud_logs_append_only
    BEFORE UPDATE OR DELETE ON fraud_logs
    FOR EACH ROW
    EXECUTE FUNCTION fn_fraud_logs_append_only();
