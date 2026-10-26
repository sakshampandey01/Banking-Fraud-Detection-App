# Repair report

Everything below is based on what was actually inspected and executed. "Not run" means it could not be executed in the
environment where this repair was done (no access to PyPI, so FastAPI / SQLAlchemy / psycopg / pydantic-settings / XGBoost
could not be installed; no `Fraud.csv`; no `best_fraud_model_tuned.pkl`).

## 1. What was in the upload

`Analysis.ipynb`, `app/` (FastAPI), `frontend/` (React 19 + Vite + Tailwind 4), `models/preprocessing.json`, `requirements.txt`.
**Not in the upload:** `Fraud.csv`, `best_fraud_model_tuned.pkl`, the `sql/` folder and `scripts/export_preprocessing.py`
(both referenced by the code/comments), `.env`, any tests, any README.

## 2. Problem checklist (found → action)

| # | Problem found | Action |
|---|---|---|
| 1 | `preprocessing.json` placeholders: `p99_amount 0`, `type_encoding {}`, scaler centre 0 / scale 1 | Cannot be computed without the dataset. `scripts/export_preprocessing.py` recomputes them from the full CSV. `type_encoding` and `night_hours` are now pre-filled from the notebook. Until the script runs, the API **refuses to score** (it would otherwise give wrong answers silently). |
| 2 | `night_hours` was `[0..5]`; notebook cell 14 uses `[0,1,2,3,4,5,22,23]` | Fixed. This silently changed `is_night` for hours 22–23. |
| 3 | `sql/` missing, so the app's stored procedure, tables and views did not exist | Written from what the code calls (`sql/01…05`). Tested on PostgreSQL 16. |
| 4 | `scripts/export_preprocessing.py` referenced but missing | Written (replays notebook cells 2, 9, 14, 18, 19, 21). |
| 5 | Startup crashed with a stack trace if model/DB/preprocessing were missing | Server always starts; `/api/health` and HTTP 503 explain what is missing (`app/runtime.py`). |
| 6 | Frontend `USE_MOCK = true` hard-coded; endpoints lacked the `/api` prefix; dataset-style rows would show as "LOW 0 %" | Mock layer deleted; real endpoints; list requests `source=API`. |
| 7 | No way to enter a transaction in the UI | Prediction form (score & save, check only), result card, account creation. |
| 8 | Validation errors (HTTP 422) had a different JSON shape than every other error | One error envelope for all errors. |
| 9 | Paths were relative to the launch directory; no `.env.example`; default DB credentials hard-coded | Paths resolved from project root; `.env.example`; default needs no password. |
| 10 | Python 3.10+ syntax but macOS ships 3.9 | Documented; `brew install python@3.12`. |
| 11 | `frontend/src/api/.Rhistory`, Vite-template `App.css`/`App.jsx` (unused) | Removed (originals are in `backup_original/`). |
| 12 | Account-opening had no code path, so no way to create accounts to test with | `fn_open_account`, `POST /api/accounts`, optional demo seed. |

## 3. Discrepancies in the notebook (reported, NOT silently changed)

1. **The decision threshold was tuned on a different model than the one saved.**
   Cell 27 computes `0.9084` from the *untuned* `models['XGBoost']` (cell 23: 100 trees, depth 6). Cell 30 trains a
   *tuned* `xgb_tuned` (200 trees, depth 4, `min_child_weight=50`); cell 36 rebuilds `models` with the tuned models and saves
   `models[best_model_name]` (the tuned one) next to the **untuned** model's threshold. Cell 38's own output shows the
   consequence: precision 0.290 / recall 0.897 at that threshold, whereas cell 27 reported 0.347 / 0.900. The app keeps
   the artifact's threshold (`0.9083510041236877`) as you asked; the export script prints what cell 27's rule would give
   for the saved model so you can decide deliberately. Nothing was retrained.
2. The notebook reads `data.csv`; the project uses `Fraud.csv`. Same schema (cell 2 output matches).
3. The scaler is fitted on **all nine columns, including** the binary flags, `step`, and `type_enc`. This is reproduced
   exactly (scikit-learn sets scale = 1 where a column's IQR is 0).
4. Cell 36 selects `best_model_name` from the *untuned* results table; it happens to be XGBoost either way.
5. Not verifiable here: that the pickle's feature list is the expected 9 names, and that its threshold equals
   `0.9083510041236877`. The export script checks both when the model file is present, as does `tests/test_real_artifact.py`.

## 4. Balance-effect assumption (the one thing not taken from your notebook)

The application's code uses `transaction_types.origin_effect / dest_effect` (+1 / −1) to decide how a transaction moves
balances and what the model's two balance features should be. Your upload had no SQL, so I seeded PaySim's documented
semantics: `CASH_IN` +1/−1, all other types −1/+1; merchant (`M…`) balances are not tracked (the dataset has 0 there, notebook cell 6).
`export_preprocessing.py` prints the movement actually observed in your `Fraud.csv` per type and says
`matches seed` or `CHECK`. If it says CHECK, edit `sql/02_seed_reference.sql` and re-run `python scripts/init_db.py`.

## 5. Files changed or added

* **Replaced:** `app/config.py`, `app/database.py`, `app/errors.py`, `app/main.py`, `app/dependencies.py`, `app/ml/features.py`,
  `app/ml/model_service.py`, `app/services/transaction_service.py`, `app/schemas/transaction.py`, `app/routers/{transactions,accounts}.py`,
  `models/preprocessing.json`, `requirements.txt`, `frontend/src/{api,hooks/useDashboardData,lib/constants,lib/transactionModel,components/{Dashboard,TransactionTable,RiskMetricsBar}}`, `frontend/package.json` (test script only), `frontend/index.html` (title).
* **Added:** `app/runtime.py`, `app/routers/predict.py`, `sql/*`, `scripts/*`, `tests/*`, `frontend/tests/*`,
  `frontend/src/components/{PredictionForm,ResultCard,HealthBanner}.jsx`, `frontend/src/lib/formValidation.js`,
  `.env.example`, `frontend/.env.example`, `requirements-dev.txt`, `.gitignore`, `pytest.ini`, `README.md`, `docs/REPORT.md`.
* **Untouched:** `Analysis.ipynb`, other frontend components and styling. Originals of everything replaced: `backup_original/`.

## 6. Test results: what actually ran

Environment: Linux, Python 3.13, Node 22, PostgreSQL 16.15 (real server), Chromium via Playwright, esbuild, Tailwind 4.3.3.

### Passed (executed)

| Suite | Result | Data |
|---|---|---|
| `tests/test_features.py` (31): formulas, feature order, `is_night` incl. 22/23, strict `> p99`, scaling formula, single = batch, type encoding, SQL seed = model encoding, 12 invalid-config cases, placeholder config refused | 31 passed | synthetic |
| `tests/test_model_service.py` (22): artifact format, probabilities in [0,1], column selection by name, missing/corrupt/malformed artifacts, bad thresholds, risk boundaries = SQL rounding | 22 passed | **synthetic scikit-learn model, not your XGBoost** |
| `tests/test_runtime.py` (8): readiness/degradation logic, DB-encoding mismatch, DB down then recovered | 8 passed | synthetic |
| `tests/test_export_preprocessing.py` (16): script output **bit-identical** to a literal copy of the notebook code (p99, encoding, scaler, and the scaled test matrix to 1e-12); backups; friendly errors; model check | 16 passed | synthetic CSV |
| Export script at full scale | ran on a generated 6,362,620-row CSV: 10 s, 1.2 GB peak; all notebook row-count cross-checks matched (rows, 8,213 frauds, 63,627 above p99, 1,272,524 test rows) | **synthetic**: confirms speed/memory/logic, not your real values |
| `tests/test_sql.py` → `tests/sql/test_database.sql` (≈40 assertions): seeds, `fn_open_account`, LOW/MEDIUM/HIGH flows, merchant handling, CASH_IN, thresholds, audit trigger, all error codes FD001–FD006 and rollback, constraints, view columns = `TransactionOut`, history query, materialised view, exact stats query; schema re-run idempotent | 3 passed | PostgreSQL 16, synthetic rows (rolled back) |
| `tests/sql/test_concurrency.sh`: two simultaneous 800-transfers from a 1000 balance → exactly one succeeds, no overdraft | passed | PostgreSQL 16 |
| `frontend/tests/lib.test.mjs` (23): endpoint URLs, request bodies, response adapters, error envelope handling, network failure, filters/metrics, empty list, form validation | 23 passed | fake `fetch` |
| Browser test (Chromium, real bundled React app, 12 checks): empty state, validation, LOW and HIGH flows, backend errors shown, check-only mode, account creation, stale data on error, degraded banner, no JS errors, 390 px no sideways scroll, API unreachable | 12 passed | **stand-in API that mimics the JSON contract, not your FastAPI** |
| All Python files compile; whole frontend bundles with esbuild; Tailwind CSS compiles | ok | – |

Totals: **80 Python tests passed (+ ≈40 SQL assertions inside them), 23 JS tests passed, 12 browser checks passed, 2 Python modules skipped, 0 failed.**

### Could NOT be run here (and why)

| Not run | Reason | How it gets run |
|---|---|---|
| **`tests/test_api.py`**: every HTTP endpoint, API ↔ database, evaluate/predict/batch, error responses, `/docs`, stats shape (≈17 tests, written) | FastAPI, SQLAlchemy, psycopg, httpx can't be installed (network policy blocks PyPI) | `pip install -r requirements-dev.txt`; `TEST_DATABASE_URL=… python -m pytest tests/test_api.py -v` |
| **`tests/test_real_artifact.py`**: your real XGBoost model: threshold, feature order, known fraud rows flagged | model file and xgboost unavailable | runs automatically once the model + generated `preprocessing.json` exist |
| **The real model scoring anything**: no real prediction was produced during this work | no model file | after step 7 try the form; the export script also reproduces notebook cell 38 |
| `scripts/export_preprocessing.py` on **your** `Fraud.csv` | file not provided | `python scripts/export_preprocessing.py` |
| `scripts/init_db.py` (needs psycopg/SQLAlchemy). Its SQL was run through `psql` and passes | – | `python scripts/init_db.py --demo` |
| Backend startup/`/api/health`/`/docs` with real FastAPI; `app/config.py` with real pydantic-settings (path logic only checked with a stand-in) | packages unavailable | `uvicorn app.main:app` |
| Full frontend ↔ **real** backend integration; `vite build`, `npm run lint` | npm registry blocked; stand-in API used instead | `npm install && npm run build && npm run lint` |
| macOS specifics (Homebrew, libomp, Apple-silicon XGBoost wheel) | Linux environment | README steps 2–3 |

Static type check (pyright) of the backend ran with unresolved imports; its remaining notes are type-stub noise, not runtime errors.

## 7. If the export script reports a difference

* `DIFFERS rows / fraud rows / above p99 / test rows`: `Fraud.csv` is not the dataset the notebook ran on (e.g. modified or a different PaySim copy). The values it writes are then correct for *that* file but won't match the saved model's training.
* `RESULT: DIFFERS from notebook cell 38`: usually a different xgboost/scikit-learn version than at training time (small drift, reported as "very close"), otherwise a different model/data pairing. Don't trust predictions until explained.
* `observed effect … CHECK`: see section 4.

## 8. Known limits / suggestions

* The historical dataset is **not** loaded into PostgreSQL (the dashboard counts transactions scored through this app; the "dataset" counters stay 0). `transactions.source='DATASET'`, `is_fraud_label` and `mv_fraud_summary` are ready if you want to import it later.
* Threshold choice: see 3.1. A dedicated threshold study on the *tuned* model is worth doing before real use.
* `MEDIUM` (≥ 0.5) is an application-level rule (existing setting), not from the notebook.
* No authentication: anyone who can reach the API can score, unblock accounts and open accounts. Fine for local use; add auth before exposing it.
