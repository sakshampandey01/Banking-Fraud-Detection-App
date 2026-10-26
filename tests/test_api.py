"""HTTP API + database integration tests (FastAPI TestClient against a REAL PostgreSQL database).

Skipped automatically unless ALL of these are available (they are on your Mac after `pip install -r
requirements-dev.txt`, with PostgreSQL running):
  * fastapi, sqlalchemy, psycopg, httpx installed
  * TEST_DATABASE_URL set, e.g.  TEST_DATABASE_URL=postgresql+psycopg://localhost:5432/fraud_test
    (an EMPTY throw-away database: the tests apply sql/*.sql and then DELETE its rows)

The model is a SYNTHETIC scikit-learn model with a controllable output, so the full request path can be
tested without your XGBoost file. Run:   TEST_DATABASE_URL=... python -m pytest tests/test_api.py -v
"""
import os

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("sqlalchemy")
pytest.importorskip("psycopg")

TEST_DB = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DB, reason="TEST_DATABASE_URL not set (needs a throw-away PostgreSQL database)")

import json  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

from conftest import ROOT, verified_config  # noqa: E402


class FixedModel:
    """predict_proba returns a probability steered by the amount: >=900000 -> 0.97, >=50000 -> 0.60, else 0.02."""
    def predict_proba(self, X):
        a = X["amount"].to_numpy()          # SCALED amount: (amount - 74000) / 120000 with the test config
        amount = a * 120_000.0 + 74_000.0
        p = np.where(amount >= 900_000, 0.97, np.where(amount >= 50_000, 0.60, 0.02))
        return np.column_stack([1 - p, p])


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    import joblib

    d = tmp_path_factory.mktemp("api")
    pre = d / "preprocessing.json"
    pre.write_text(json.dumps(verified_config()))
    pkl = d / "model.pkl"
    from app.ml.features import FEATURES
    joblib.dump({"model_name": "SYNTHETIC-API-TEST", "model": FixedModel(), "threshold": 0.9083510041236877,
                 "features": FEATURES}, pkl)
    os.environ.update(DATABASE_URL=TEST_DB, MODEL_PATH=str(pkl), PREPROCESSING_PATH=str(pre))

    from app.config import get_settings
    get_settings.cache_clear()
    engine = create_engine(TEST_DB)
    with engine.begin() as conn:
        for f in ("00_drop_all.sql", "01_schema.sql", "02_seed_reference.sql", "03_routines.sql", "04_views.sql"):
            conn.exec_driver_sql((ROOT / "sql" / f).read_text())
    import app.main as main
    with TestClient(main.app) as c:
        yield c
    engine.dispose()


def open_account(client, number, balance):
    r = client.post("/api/accounts", json={"account_number": number, "balance": balance})
    assert r.status_code == 201, r.text
    return r.json()


def test_health_ready(client):
    h = client.get("/api/health").json()
    assert h["status"] == "ok" and h["ready_for_scoring"] and h["model"]["name"] == "SYNTHETIC-API-TEST"
    assert h["database"] == {"connected": True, "type_encoding_verified": True}


def test_docs_and_openapi_available(client):
    assert client.get("/docs").status_code == 200
    paths = client.get("/openapi.json").json()["paths"]
    for p in ("/api/predict", "/api/predict/batch", "/api/transactions/evaluate", "/api/transactions", "/api/stats", "/api/accounts"):
        assert p in paths


PREDICT = dict(type="TRANSFER", amount=181, step=1, old_balance_orig=181, new_balance_orig=0, old_balance_dest=0, new_balance_dest=181)


def test_predict_single_and_levels(client):
    low = client.post("/api/predict", json=PREDICT).json()
    assert low["risk_level"] == "LOW" and low["is_fraud"] is False and 0 <= low["fraud_probability"] <= 1
    assert low["decision_threshold"] == pytest.approx(0.908351)
    mid = client.post("/api/predict", json={**PREDICT, "amount": 60000}).json()
    assert mid["risk_level"] == "MEDIUM"
    high = client.post("/api/predict", json={**PREDICT, "amount": 950000}).json()
    assert high["risk_level"] == "HIGH" and high["is_fraud"] is True


def test_predict_batch(client):
    r = client.post("/api/predict/batch", json={"transactions": [PREDICT, {**PREDICT, "amount": 950000}]}).json()
    assert r["count"] == 2 and [x["risk_level"] for x in r["results"]] == ["LOW", "HIGH"]


@pytest.mark.parametrize("patch", [
    {"type": "REFUND"}, {"amount": 0}, {"amount": -5}, {"amount": "abc"}, {"step": 0}, {"step": 744},
    {"old_balance_orig": -1}, {"amount": 1.234},
])
def test_predict_rejects_invalid_input(client, patch):
    r = client.post("/api/predict", json={**PREDICT, **patch})
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_predict_rejects_missing_fields_and_empty_batch(client):
    assert client.post("/api/predict", json={"type": "TRANSFER"}).status_code == 422
    assert client.post("/api/predict/batch", json={"transactions": []}).status_code == 422


def test_evaluate_stores_transaction_and_updates_dashboard(client):
    open_account(client, "C800000001", 100000)
    open_account(client, "C800000002", 0)
    before = client.get("/api/stats").json()
    r = client.post("/api/transactions/evaluate", json={"type": "TRANSFER", "amount": 1000, "orig_account": "C800000001", "dest_account": "C800000002", "step": 5})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["risk_level"] == "LOW" and body["status"] == "COMPLETED" and body["model_name"] == "SYNTHETIC-API-TEST"
    after = client.get("/api/stats").json()
    assert after["live"]["evaluated"] == before["live"]["evaluated"] + 1 and after["live"]["low"] == before["live"]["low"] + 1
    row = client.get(f"/api/transactions/{body['txn_id']}").json()
    assert row["orig_account"] == "C800000001" and row["fraud_probability"] == pytest.approx(0.02)
    assert client.get("/api/accounts/C800000002").json()["balance"] in ("1000.00", 1000.0, "1000")
    assert body["txn_id"] in [t["txn_id"] for t in client.get("/api/transactions", params={"source": "API"}).json()]
    assert body["txn_id"] in [t["txn_id"] for t in client.get("/api/transactions/C800000001").json()]


def test_high_risk_blocks_transaction_and_account(client):
    open_account(client, "C800000003", 5_000_000)
    open_account(client, "C800000004", 0)
    r = client.post("/api/transactions/evaluate", json={"type": "TRANSFER", "amount": 950000, "orig_account": "C800000003", "dest_account": "C800000004"}).json()
    assert r["risk_level"] == "HIGH" and r["status"] == "BLOCKED" and r["origin_account_status"] == "BLOCKED" and r["is_fraud"]
    assert client.get("/api/accounts/C800000004").json()["balance"] in ("0.00", 0.0, "0")
    audit = client.get("/api/accounts/C800000003/audit").json()
    assert audit and audit[0]["new_status"] == "BLOCKED"
    again = client.post("/api/transactions/evaluate", json={"type": "TRANSFER", "amount": 10, "orig_account": "C800000003", "dest_account": "C800000004"})
    assert again.status_code == 423 and again.json()["error"]["code"] == "ACCOUNT_BLOCKED"
    unblock = client.patch("/api/accounts/C800000003/status", json={"status": "ACTIVE", "reason": "false positive"})
    assert unblock.status_code == 200 and unblock.json()["status"] == "ACTIVE"


@pytest.mark.parametrize("body,status,code", [
    ({"type": "TRANSFER", "amount": 10, "orig_account": "C899999999", "dest_account": "C800000002"}, 404, "ACCOUNT_NOT_FOUND"),
    ({"type": "TRANSFER", "amount": 10, "orig_account": "C800000001", "dest_account": "C800000001"}, 422, "SAME_ACCOUNT"),
    ({"type": "TRANSFER", "amount": 99999999, "orig_account": "C800000001", "dest_account": "C800000002"}, 422, "INSUFFICIENT_FUNDS"),
    ({"type": "TRANSFER", "amount": 10, "orig_account": "bad", "dest_account": "C800000002"}, 422, "VALIDATION_ERROR"),
    ({"type": "NOPE", "amount": 10, "orig_account": "C800000001", "dest_account": "C800000002"}, 422, "VALIDATION_ERROR"),
])
def test_evaluate_errors_are_meaningful_and_write_nothing(client, body, status, code):
    count = lambda: client.get("/api/stats").json()["live"]["evaluated"]
    before = count()
    r = client.post("/api/transactions/evaluate", json=body)
    assert r.status_code == status and r.json()["error"]["code"] == code and r.json()["error"]["message"]
    assert count() == before


def test_account_creation_conflict_and_lookup(client):
    open_account(client, "C800000010", 5)
    assert client.post("/api/accounts", json={"account_number": "C800000010"}).status_code == 409
    assert client.get("/api/accounts/C800000099").status_code == 404
    assert client.post("/api/accounts", json={"account_number": "X1"}).status_code == 422
    assert any(a["account_number"] == "C800000010" for a in client.get("/api/accounts").json())


def test_stats_shape_matches_frontend_adapter(client):
    s = client.get("/api/stats").json()
    assert set(s) == {"total_transactions", "transactions_today", "fraud_flagged", "blocked_accounts", "live", "dataset"}
    assert set(s["live"]) == {"evaluated", "today", "high", "medium", "low"}
    assert client.get("/api/stats/summary").status_code == 200
