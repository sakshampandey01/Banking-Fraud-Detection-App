-- =====================================================================
-- 01_schema.sql  --  Core relational schema (PostgreSQL 14+)
-- Run FIRST. Re-runnable: drops existing objects (dev convenience!).
--
-- Normalization notes (3NF):
--   users             : one row per account holder (customer or merchant)
--   accounts          : 1 user -> N accounts; balance + status live here only
--   transaction_types : lookup table (no repeating type strings, holds the
--                       debit/credit rules + the ML label encoding)
--   transactions      : ledger of money movements
--   fraud_logs        : 1:1 with transactions evaluated by the ML model
--   account_audit     : history of every account status change (trigger-fed)
-- =====================================================================

DROP VIEW  IF EXISTS v_transaction_details CASCADE;
DROP MATERIALIZED VIEW IF EXISTS mv_fraud_summary CASCADE;
DROP TABLE IF EXISTS account_audit, fraud_logs, transactions, accounts,
                     users, transaction_types CASCADE;

-- ---------------------------------------------------------------------
-- users
-- ---------------------------------------------------------------------
CREATE TABLE users (
    user_id      BIGSERIAL    PRIMARY KEY,
    external_ref VARCHAR(20)  NOT NULL UNIQUE,          -- e.g. 'C1231006815' / 'M1979787155'
    user_type    VARCHAR(10)  NOT NULL
                 CHECK (user_type IN ('CUSTOMER', 'MERCHANT')),
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- accounts
-- ---------------------------------------------------------------------
CREATE TABLE accounts (
    account_id     BIGSERIAL     PRIMARY KEY,
    user_id        BIGINT        NOT NULL REFERENCES users(user_id),
    account_number VARCHAR(20)   NOT NULL UNIQUE,
    balance        NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (balance >= 0),
    status         VARCHAR(10)   NOT NULL DEFAULT 'ACTIVE'
                   CHECK (status IN ('ACTIVE', 'BLOCKED')),
    opened_at      TIMESTAMPTZ   NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- transaction_types  (lookup + business rules + ML encoding)
--   origin_effect / dest_effect: +1 = account is credited, -1 = debited
--   type_enc: MUST equal the LabelEncoder output used in the notebook
--             (alphabetical: CASH_IN=0 ... TRANSFER=4). The API verifies
--             this at startup and refuses to boot on a mismatch.
-- ---------------------------------------------------------------------
CREATE TABLE transaction_types (
    type_code     VARCHAR(10) PRIMARY KEY,
    type_enc      SMALLINT    NOT NULL UNIQUE,
    origin_effect SMALLINT    NOT NULL CHECK (origin_effect IN (-1, 1)),
    dest_effect   SMALLINT    NOT NULL CHECK (dest_effect   IN (-1, 1)),
    description   VARCHAR(100)
);

INSERT INTO transaction_types VALUES
    ('CASH_IN',  0,  1, -1, 'Customer deposits cash (origin credited)'),
    ('CASH_OUT', 1, -1,  1, 'Customer withdraws cash'),
    ('DEBIT',    2, -1,  1, 'Debit to a bank account'),
    ('PAYMENT',  3, -1,  1, 'Payment to a merchant'),
    ('TRANSFER', 4, -1,  1, 'Account-to-account transfer');

-- ---------------------------------------------------------------------
-- transactions
--   step = simulated hour (1..743), same unit as the dataset.
--   is_fraud_label / is_flagged_fraud_rule are ground truth from the CSV
--   (NULL for live API transactions).
-- ---------------------------------------------------------------------
CREATE TABLE transactions (
    txn_id                BIGSERIAL     PRIMARY KEY,
    step                  INTEGER       NOT NULL CHECK (step >= 1),
    type_code             VARCHAR(10)   NOT NULL REFERENCES transaction_types(type_code),
    amount                NUMERIC(18,2) NOT NULL CHECK (amount >= 0),
    orig_account_id       BIGINT        NOT NULL REFERENCES accounts(account_id),
    dest_account_id       BIGINT        NOT NULL REFERENCES accounts(account_id),
    old_balance_orig      NUMERIC(18,2) NOT NULL,
    new_balance_orig      NUMERIC(18,2) NOT NULL,
    old_balance_dest      NUMERIC(18,2) NOT NULL,
    new_balance_dest      NUMERIC(18,2) NOT NULL,
    status                VARCHAR(10)   NOT NULL DEFAULT 'COMPLETED'
                          CHECK (status IN ('COMPLETED', 'BLOCKED')),
    source                VARCHAR(10)   NOT NULL DEFAULT 'API'
                          CHECK (source IN ('API', 'DATASET')),
    is_fraud_label        BOOLEAN,
    is_flagged_fraud_rule BOOLEAN,
    created_at            TIMESTAMPTZ   NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- fraud_logs : one row per ML decision (append-only, see trigger file)
-- ---------------------------------------------------------------------
CREATE TABLE fraud_logs (
    log_id            BIGSERIAL    PRIMARY KEY,
    txn_id            BIGINT       NOT NULL UNIQUE REFERENCES transactions(txn_id),
    fraud_probability NUMERIC(7,6) NOT NULL CHECK (fraud_probability BETWEEN 0 AND 1),
    risk_level        VARCHAR(6)   NOT NULL CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH')),
    action_taken      VARCHAR(20)  NOT NULL
                      CHECK (action_taken IN ('APPROVED', 'APPROVED_FLAGGED', 'BLOCKED')),
    model_name        VARCHAR(50)  NOT NULL,
    model_threshold   NUMERIC(7,6) NOT NULL,
    logged_at         TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- account_audit : filled automatically by a trigger on accounts.status
-- ---------------------------------------------------------------------
CREATE TABLE account_audit (
    audit_id   BIGSERIAL   PRIMARY KEY,
    account_id BIGINT      NOT NULL REFERENCES accounts(account_id),
    old_status VARCHAR(10) NOT NULL,
    new_status VARCHAR(10) NOT NULL,
    reason     TEXT        NOT NULL,
    changed_by TEXT        NOT NULL DEFAULT current_user,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
