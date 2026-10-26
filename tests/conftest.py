"""Shared test fixtures.

IMPORTANT - everything produced here is SYNTHETIC test data. It is used to exercise the code
paths, never to report results about the real dataset or the real model:

  * make_paysim_csv()      a small PaySim-shaped CSV (NOT the real Fraud.csv)
  * synthetic_artifact()   a tiny scikit-learn model saved in the same dict format as the notebook's
                           best_fraud_model_tuned.pkl (NOT the user's XGBoost model)

Tests that need the real model are in test_real_artifact.py and are skipped unless the file exists.
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.ml.features import (  # noqa: E402
    DEFAULT_TYPE_ENCODING, FEATURES, NOTEBOOK_NIGHT_HOURS, STATUS_VERIFIED,
)

TYPES = list(DEFAULT_TYPE_ENCODING)           # alphabetical, like LabelEncoder
SIGNS = {"CASH_IN": (+1, -1), "CASH_OUT": (-1, +1), "DEBIT": (-1, +1), "PAYMENT": (-1, +1), "TRANSFER": (-1, +1)}


def make_paysim_csv(path: Path, n: int = 30_000, seed: int = 7) -> Path:
    """Write a synthetic PaySim-like CSV with the 11 original columns."""
    rng = np.random.default_rng(seed)
    types = rng.choice(TYPES, size=n, p=[0.22, 0.35, 0.01, 0.34, 0.08])
    amount = np.round(rng.lognormal(mean=9.0, sigma=1.6, size=n), 2)
    old_o = np.round(amount * rng.uniform(0.8, 6.0, size=n) * (rng.random(n) > 0.3), 2)
    old_d = np.round(amount * rng.uniform(0.0, 8.0, size=n) * (rng.random(n) > 0.4), 2)
    sign_o = np.array([SIGNS[t][0] for t in types])
    sign_d = np.array([SIGNS[t][1] for t in types])
    new_o = np.maximum(old_o + sign_o * amount, 0).round(2)
    new_d = np.maximum(old_d + sign_d * amount, 0).round(2)
    merchant = types == "PAYMENT"
    old_d[merchant] = 0.0
    new_d[merchant] = 0.0
    fraud_candidate = np.isin(types, ["TRANSFER", "CASH_OUT"])
    is_fraud = ((rng.random(n) < 0.03) & fraud_candidate).astype(int)
    df = pd.DataFrame({
        "step": rng.integers(1, 744, size=n),
        "type": types,
        "amount": amount,
        "nameOrig": ["C" + str(i) for i in rng.integers(10**8, 10**9, size=n)],
        "oldbalanceOrg": old_o,
        "newbalanceOrig": new_o,
        "nameDest": [("M" if m else "C") + str(i) for m, i in zip(merchant, rng.integers(10**8, 10**9, size=n))],
        "oldbalanceDest": old_d,
        "newbalanceDest": new_d,
        "isFraud": is_fraud,
        "isFlaggedFraud": 0,
    })
    df.to_csv(path, index=False)
    return path


@pytest.fixture(scope="session")
def paysim_csv(tmp_path_factory) -> Path:
    return make_paysim_csv(tmp_path_factory.mktemp("data") / "Fraud.csv")


def verified_config(p99: float = 200_000.0) -> dict:
    """A syntactically valid, VERIFIED-looking config with arbitrary (synthetic) scaler values."""
    return {
        "_meta": {"status": STATUS_VERIFIED, "synthetic": True},
        "features": list(FEATURES),
        "p99_amount": p99,
        "night_hours": list(NOTEBOOK_NIGHT_HOURS),
        "type_encoding": dict(DEFAULT_TYPE_ENCODING),
        "scaler_center": [372.0, 74_000.0, 11.2, 0.0, 12.0, 0.0, 2_000.0, 0.0, 3.0],
        "scaler_scale": [250.0, 120_000.0, 2.0, 1.0, 12.0, 1.0, 100_000.0, 150_000.0, 2.0],
    }


@pytest.fixture()
def config() -> dict:
    return verified_config()


def synthetic_artifact(path: Path, threshold: float = 0.9083510041236877, seed: int = 0) -> Path:
    """SYNTHETIC stand-in for best_fraud_model_tuned.pkl (same dict layout, tiny sklearn model)."""
    from sklearn.ensemble import GradientBoostingClassifier

    rng = np.random.default_rng(seed)
    X = pd.DataFrame(rng.normal(size=(600, len(FEATURES))), columns=FEATURES)
    y = (X["amount"] + X["balance_diff_orig"] + rng.normal(scale=0.5, size=len(X)) > 1.2).astype(int)
    model = GradientBoostingClassifier(n_estimators=15, max_depth=2, random_state=seed).fit(X, y)
    joblib.dump({"model_name": "SYNTHETIC-TEST-MODEL", "model": model,
                 "threshold": threshold, "features": list(FEATURES)}, path)
    return path


@pytest.fixture(scope="session")
def artifact_path(tmp_path_factory) -> Path:
    return synthetic_artifact(tmp_path_factory.mktemp("model") / "best_fraud_model_tuned.pkl")
