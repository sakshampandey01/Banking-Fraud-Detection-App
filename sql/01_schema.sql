-- =====================================================================================
-- Bank Fraud Detection - core schema (PostgreSQL 14 or newer). Safe to run repeatedly.
--
-- Every table and column below exists because the application code reads or writes it:
--   app/services/transaction_service.py, app/routers/*.py, app/schemas/transaction.py.
-- Run via:  python scripts/init_db.py      (or: psql "$DB" -f sql/01_schema.sql ...)
-- =====================================================================================

-- A person or business. The application only needs the type (MERCHANT destinations have
-- untracked balances, exactly like the PaySim dataset the model was trained on).
CREATE TABLE IF NOT EXISTS users (
    user_id     BIGSERIAL   PRIMARY KEY,
    user_type   TEXT        NOT NULL CHECK (user_type IN ('CUSTOMER', 'MERCHANT')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- account_number follows the dataset's naming: C<digits> customers, M<digits> merchants
-- (the same pattern the API validates in app/schemas/transaction.py).
CREATE TABLE IF NOT EXISTS accounts (
    account_id      BIGSERIAL     PRIMARY KEY,
    user_id         BIGINT        NOT NULL REFERENCES users (user_id),
    account_number  TEXT          NOT NULL UNIQUE CHECK (account_number ~ '^[CM][0-9]{1,18}$'),
    balance         NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (balance >= 0),
    status          TEXT          NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'BLOCKED')),
    opened_at       TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_accounts_user    ON accounts (user_id);
-- stats endpoint: "SELECT COUNT(*) FROM accounts WHERE status = 'BLOCKED'"
CREATE INDEX IF NOT EXISTS idx_accounts_blocked ON accounts (account_id) WHERE status = 'BLOCKED';

-- Reference data. type_enc MUST equal the LabelEncoder code the model was trained with
-- (models/preprocessing.json "type_encoding"); the API refuses to start scoring if they differ.
-- origin_effect / dest_effect: how the transaction moves the balance (-1 down, +1 up, 0 none).
CREATE TABLE IF NOT EXISTS transaction_types (
    type_code      TEXT     PRIMARY KEY CHECK (type_code IN ('CASH_IN', 'CASH_OUT', 'DEBIT', 'PAYMENT', 'TRANSFER')),
    type_enc       SMALLINT NOT NULL UNIQUE CHECK (type_enc >= 0),
    origin_effect  SMALLINT NOT NULL CHECK (origin_effect IN (-1, 0, 1)),
    dest_effect    SMALLINT NOT NULL CHECK (dest_effect   IN (-1, 0, 1)),
    description    TEXT
);

-- The ledger. source = 'API' for transactions scored by this application, 'DATASET' for
-- historical PaySim rows imported from the original dataset, if you choose to load it (is_fraud_label = isFraud).
CREATE TABLE IF NOT EXISTS transactions (
    txn_id             BIGSERIAL     PRIMARY KEY,
    step               INTEGER       NOT NULL CHECK (step >= 1),
    type_code          TEXT          NOT NULL REFERENCES transaction_types (type_code),
    amount             NUMERIC(16,2) NOT NULL CHECK (amount >= 0),
    orig_account_id    BIGINT        NOT NULL REFERENCES accounts (account_id),
    dest_account_id    BIGINT        NOT NULL REFERENCES accounts (account_id),
    old_balance_orig   NUMERIC(18,2) NOT NULL,
    new_balance_orig   NUMERIC(18,2) NOT NULL,
    old_balance_dest   NUMERIC(18,2) NOT NULL,
    new_balance_dest   NUMERIC(18,2) NOT NULL,
    status             TEXT          NOT NULL CHECK (status IN ('COMPLETED', 'BLOCKED')),
    source             TEXT          NOT NULL DEFAULT 'API' CHECK (source IN ('API', 'DATASET')),
    is_fraud_label     BOOLEAN,                       -- only known for DATASET rows
    created_at         TIMESTAMPTZ   NOT NULL DEFAULT now()
);
-- account history reads each side through its own index (see _ACCOUNT_TXNS_SQL in routers/transactions.py)
CREATE INDEX IF NOT EXISTS idx_txn_orig_step ON transactions (orig_account_id, step);
CREATE INDEX IF NOT EXISTS idx_txn_dest      ON transactions (dest_account_id);
-- dashboard feed: newest API transactions without scanning millions of dataset rows
CREATE INDEX IF NOT EXISTS idx_txn_api_recent ON transactions (txn_id DESC) WHERE source = 'API';

-- One row per transaction scored by the model (stats endpoints count these, so the table stays small).
CREATE TABLE IF NOT EXISTS fraud_logs (
    log_id              BIGSERIAL    PRIMARY KEY,
    txn_id              BIGINT       NOT NULL UNIQUE REFERENCES transactions (txn_id),
    fraud_probability   NUMERIC(7,6) NOT NULL CHECK (fraud_probability BETWEEN 0 AND 1),
    risk_level          TEXT         NOT NULL CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH')),
    action_taken        TEXT         NOT NULL CHECK (action_taken IN ('APPROVED', 'APPROVED_FLAGGED', 'BLOCKED')),
    model_name          TEXT         NOT NULL,
    decision_threshold  NUMERIC(7,6) NOT NULL,
    logged_at           TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_fraud_logs_risk      ON fraud_logs (risk_level);
CREATE INDEX IF NOT EXISTS idx_fraud_logs_logged_at ON fraud_logs (logged_at);

-- Written by the trigger in 03_routines.sql whenever an account's status changes.
CREATE TABLE IF NOT EXISTS account_audit (
    audit_id    BIGSERIAL   PRIMARY KEY,
    account_id  BIGINT      NOT NULL REFERENCES accounts (account_id),
    old_status  TEXT        NOT NULL,
    new_status  TEXT        NOT NULL,
    reason      TEXT        NOT NULL,
    changed_by  TEXT        NOT NULL,
    changed_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_audit_account ON account_audit (account_id, changed_at DESC);
