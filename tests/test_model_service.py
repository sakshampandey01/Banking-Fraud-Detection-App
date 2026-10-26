"""Model loading and probabilities. Uses a SYNTHETIC scikit-learn model in the notebook's artifact format.

The user's real XGBoost model is NOT used here - see test_real_artifact.py for the tests that use it.
"""
import joblib
import numpy as np
import pandas as pd
import pytest

from app.ml.features import FEATURES, FeatureBuilder
from app.ml.model_service import FraudModel, ModelUnavailable, classify_risk
from conftest import verified_config


def test_loads_artifact_in_notebook_format(artifact_path):
    m = FraudModel.load(artifact_path)
    assert m.name == "SYNTHETIC-TEST-MODEL"
    assert m.threshold == pytest.approx(0.9083510041236877)
    assert m.features == FEATURES


def test_predict_proba_is_a_probability_for_single_and_batch(artifact_path):
    m = FraudModel.load(artifact_path)
    fb = FeatureBuilder(verified_config())
    X = fb.build_many(type_codes=["TRANSFER", "PAYMENT", "CASH_OUT"], amounts=[181.0, 9839.64, 5e6],
                      steps=[1, 26, 400], balance_diff_orig=[181.0, 9839.64, 5e6], balance_diff_dest=[0.0, 0.0, 5e6])
    probs = m.predict_proba_many(X)
    assert len(probs) == 3 and all(0.0 <= p <= 1.0 and np.isfinite(p) for p in probs)
    assert m.predict_proba(X.iloc[[0]]) == pytest.approx(probs[0])


def test_columns_are_selected_by_name_not_position(artifact_path):
    m = FraudModel.load(artifact_path)
    X = FeatureBuilder(verified_config()).build(type_code="TRANSFER", amount=500.0, step=3,
                                                 balance_diff_orig=500.0, balance_diff_dest=500.0)
    shuffled = X[list(reversed(FEATURES))]
    assert m.predict_proba(shuffled) == pytest.approx(m.predict_proba(X))


def test_missing_model_file_explains_how_to_fix(tmp_path):
    with pytest.raises(ModelUnavailable, match="models/"):
        FraudModel.load(tmp_path / "best_fraud_model_tuned.pkl")


@pytest.mark.parametrize("artifact,match", [
    ([1, 2, 3], "must contain a dict"),
    ({"model": object(), "threshold": 0.9}, "missing keys"),
    ({"model": object(), "threshold": 0.9, "features": FEATURES}, "predict_proba"),
])
def test_malformed_artifacts_are_rejected(tmp_path, artifact, match):
    p = tmp_path / "m.pkl"
    joblib.dump(artifact, p)
    with pytest.raises(ModelUnavailable, match=match):
        FraudModel.load(p)


@pytest.mark.parametrize("threshold", [0.0, 1.0, 1.5, -0.1, float("nan")])
def test_invalid_threshold_is_rejected(tmp_path, threshold):
    from sklearn.dummy import DummyClassifier
    p = tmp_path / "m.pkl"
    joblib.dump({"model": DummyClassifier().fit([[0], [1]], [0, 1]), "threshold": threshold, "features": FEATURES}, p)
    with pytest.raises(ModelUnavailable, match="threshold"):
        FraudModel.load(p)


def test_corrupt_pickle_is_reported_not_raised_raw(tmp_path):
    p = tmp_path / "m.pkl"
    p.write_bytes(b"this is not a pickle")
    with pytest.raises(ModelUnavailable, match="Could not load"):
        FraudModel.load(p)


@pytest.mark.parametrize("p,expected", [
    (0.0, "LOW"), (0.4999995, "LOW"), (0.5, "MEDIUM"), (0.9, "MEDIUM"),
    (0.908350, "MEDIUM"), (0.9083510041236877, "HIGH"), (0.95, "HIGH"), (1.0, "HIGH"),
])
def test_risk_classification_boundaries(p, expected):
    assert classify_risk(p, 0.9083510041236877, 0.5) == expected


def test_risk_classification_matches_database_rounding():
    """The procedure compares NUMERIC(7,6) values; Python rounds both sides to 6 dp so it gives the same answer."""
    thr = 0.9083510041236877                       # stored in the database as 0.908351
    assert round(0.9083508, 6) == round(thr, 6)    # same value once stored at 6 dp
    assert classify_risk(0.9083508, thr, 0.5) == "HIGH"
    assert classify_risk(0.9083504, thr, 0.5) == "MEDIUM"    # rounds to 0.908350 < 0.908351
