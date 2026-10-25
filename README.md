# Bank Fraud Detection – Backend (FastAPI + PostgreSQL + XGBoost)

```
fraud-backend/
├── app/
│   ├── main.py                  # app, lifespan (model loading), CORS, routers
│   ├── config.py                # settings from env / .env
│   ├── database.py              # SQLAlchemy engine (Core, pooled)
│   ├── dependencies.py          # injects engine / model / feature builder
│   ├── errors.py                # SQLSTATE -> HTTP error mapping
│   ├── ml/
│   │   ├── model_service.py     # loads the .pkl once, predict_proba()
│   │   └── features.py          # rebuilds the notebook's 9 features + scaling
│   ├── schemas/transaction.py   # Pydantic request/response contracts
│   ├── services/transaction_service.py   # evaluate flow: lookup -> ML -> stored procedure
│   └── routers/                 # transactions.py, accounts.py, stats.py
├── sql/
│   ├── 01_schema.sql            # tables, keys, CHECKs, lookup data
│   ├── 02_procedures.sql        # sp_process_transaction
│   ├── 03_triggers.sql          # auto-block, audit, append-only log
│   └── 04_indexes_views.sql     # (after load) indexes, view, materialized view
├── scripts/
│   ├── run_sql.py               # runs .sql files (no psql needed)
│   ├── export_preprocessing.py  # recreates the scaler you never saved
│   ├── ingest_data.py           # bulk CSV load
│   └── smoke_test.py            # end-to-end test
├── models/                      # best_fraud_model_tuned.pkl + preprocessing.json
├── data/                        # put Fraud.csv here
└── requirements.txt
```

## 1. Setup

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                    # edit DATABASE_URL
```

Create the database (psql as the postgres superuser):

```sql
CREATE USER fraud_user WITH PASSWORD 'fraud_pass';
CREATE DATABASE fraud_db OWNER fraud_user;
```

**Pin xgboost.** Run `pip show xgboost` in the environment where you trained the model and
use that exact version in `requirements.txt`. Pickled XGBoost models can behave differently
across versions.

## 2. Preprocessing file (important)

The notebook scaled all features with `RobustScaler` but only saved `{model, threshold,
features}` – **not the scaler**. Without it, live predictions would be wrong. This script
recomputes the scaler (same split: `random_state=42`, stratified), the 99th-percentile
amount cut-off and the type encoding from the CSV and stores them as JSON. A ready-made
`models/preprocessing.json` is included; regenerate it any time with:

```bash
python -m scripts.export_preprocessing --csv data/Fraud.csv
```

Check: this reproduces the notebook's test result (recall ≈ 0.90, precision ≈ 0.29).

## 3. Database

```bash
python -m scripts.run_sql sql/01_schema.sql sql/02_procedures.sql sql/03_triggers.sql
python -m scripts.ingest_data --csv data/Fraud.csv --max-rows 1000000   # dev sample, ~1 min
# python -m scripts.ingest_data --csv data/Fraud.csv --truncate          # full 6.36M rows (expect several minutes and several GB of disk)
python -m scripts.run_sql sql/04_indexes_views.sql
```

If you loaded data before running 04, refresh the materialized view:
`REFRESH MATERIALIZED VIEW mv_fraud_summary;`

### Schema

`users 1—N accounts 1—N transactions (orig/dest) 1—1 fraud_logs`, plus the lookup
`transaction_types` and the `account_audit` history.

### DBMS features to point at in your report

| Feature | Where |
|---|---|
| 3NF schema, PK/FK, CHECK, UNIQUE | `01_schema.sql` |
| Lookup table driving business rules (debit/credit direction) and ML encoding | `transaction_types` |
| Stored procedure: validation, row locking (`FOR UPDATE`, ordered), atomic write, custom error codes | `sp_process_transaction` |
| Trigger 1: HIGH-risk log → block origin account | `trg_block_account_on_high_risk` |
| Trigger 2: every status change → audit row (cascades from trigger 1) | `trg_audit_account_status` |
| Trigger 3: append-only log (UPDATE/DELETE rejected) | `trg_fraud_logs_append_only` |
| Partial indexes (fraud is ~0.13 % of rows) | `04_indexes_views.sql` |
| View + materialized view | `v_transaction_details`, `mv_fraud_summary` |
| Bulk loading (COPY into UNLOGGED staging + set-based INSERT…SELECT) | `ingest_data.py` |
| ACID transaction boundaries | `evaluate_transaction()` |

### Decision rules (live API)

| ML probability | risk_level | transaction | account |
|---|---|---|---|
| ≥ model threshold (0.908 from the .pkl) | HIGH | `BLOCKED`, money not moved | origin → `BLOCKED` by trigger |
| ≥ `MEDIUM_RISK_THRESHOLD` (0.5) | MEDIUM | `COMPLETED`, flagged | unchanged |
| otherwise | LOW | `COMPLETED` | unchanged |

Because the model's precision is ~29 %, most HIGH alerts on real data would be false
positives. That is why the API includes `PATCH /api/accounts/{n}/status` so an analyst can
unblock (the change is audited).

## 4. Run the API

```bash
uvicorn app.main:app --reload
```

Swagger UI: http://localhost:8000/docs · test everything: `python -m scripts.smoke_test`

### Evaluate a transaction

```bash
curl -X POST http://localhost:8000/api/transactions/evaluate \
  -H "Content-Type: application/json" \
  -d '{"type":"TRANSFER","amount":181,"orig_account":"C1305486145","dest_account":"C553264065","step":3}'
```
(use account numbers that exist in your loaded data)

```json
{ "txn_id": 1000003, "status": "BLOCKED", "risk_level": "HIGH", "action_taken": "BLOCKED",
  "is_fraud": true, "fraud_probability": 0.994369, "decision_threshold": 0.908351,
  "model_name": "XGBoost", "origin_account_status": "BLOCKED", "message": "..." }
```

Errors are always `{"error": {"code": "...", "message": "..."}}`:
`ACCOUNT_NOT_FOUND` 404 · `ACCOUNT_BLOCKED` 423 · `INSUFFICIENT_FUNDS` 422 · `SAME_ACCOUNT` 422
(invalid input → FastAPI's standard 422 `detail`).

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/transactions/evaluate` | score + persist via stored procedure |
| GET | `/api/transactions?limit&offset&source&status&risk_level&account` | list (newest first) |
| GET | `/api/transactions/{id}` | one transaction |
| GET | `/api/accounts/{number}` | account + balance + status |
| PATCH | `/api/accounts/{number}/status` | block / unblock with reason |
| GET | `/api/accounts/{number}/audit` | status history |
| GET | `/api/stats/summary` | dashboard numbers |
| GET | `/api/health` | DB + model check |

## 5. Things to know

* **Demo tip:** in the dataset fraud only occurs in `TRANSFER` and `CASH_OUT`. Use those types
  (night hours, e.g. `step: 3`) to see HIGH alerts; `PAYMENT` will almost always be LOW.
* **`step`** is the dataset's simulated hour (1–743). If the frontend omits it, the server derives
  it from the clock (`24*(day-1)+hour+1`).
* **Balances:** the frontend never sends balances. The server uses the stored account balance and
  the rules in `transaction_types`; merchant (`M…`) balances are not tracked, as in the dataset.
* **Startup checks:** the API refuses to start if the DB's `transaction_types.type_enc` does not
  match the model's encoding, or the feature order differs.
* **Oracle:** the logic ports directly. `sp_process_transaction` becomes a PL/SQL procedure with
  `OUT` parameters and `SELECT ... FOR UPDATE`; the triggers become `AFTER INSERT ... FOR EACH ROW
  WHEN (NEW.risk_level = 'HIGH')` (update `accounts` directly inside the trigger); `BIGSERIAL` → identity columns; `COPY` → SQL*Loader/`python-oracledb executemany`.
  The Python layer only needs `python-oracledb` and `CALL` → `cursor.callproc`. This guide's SQL was
  tested on PostgreSQL 16 only.
