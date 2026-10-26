-- =====================================================================================
-- OPTIONAL demo accounts so you can try the prediction form straight away.
--   python scripts/init_db.py --demo
-- These are made-up accounts with made-up balances (ids start with 9 so they cannot be mistaken
-- for dataset accounts). They contain no transactions and no predictions. Safe to run repeatedly.
-- =====================================================================================
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN SELECT * FROM (VALUES
        ('C900000001', 250000.00),
        ('C900000002', 250000.00),
        ('C900000003',   5000.00),
        ('C900000004', 900000.00),
        ('M900000001',      0.00),
        ('M900000002',      0.00)
    ) AS d (account_number, balance)
    LOOP
        IF NOT EXISTS (SELECT 1 FROM accounts WHERE account_number = r.account_number) THEN
            PERFORM fn_open_account(r.account_number, r.balance);
        END IF;
    END LOOP;
END;
$$;
