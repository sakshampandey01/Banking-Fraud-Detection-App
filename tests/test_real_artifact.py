"""Tests that use the REAL saved model and the REAL preprocessing.json (generated from Fraud.csv).

They are skipped (not failed, not passed) until both files exist on this machine:
    models/best_fraud_model_tuned.pkl   and   models/preprocessing.json  with status VERIFIED_FROM_DATASET
Needs the xgboost package installed (pip install -r requirements.txt).
"""
import json
import math

import pytest

pytest.importorskip("pydantic_settings")

from app.config import MODEL_FILENAME, get_settings
from app.ml.features import FEATURES, STATUS_VERIFIED, FeatureBuilder
from app.ml.model_service import FraudModel

settings = get_settings()
MODEL = settings.resolved_model_path
PRE = settings.resolved_preprocessing_path

pytestmark = [
    pytest.mark.skipif(not MODEL.exists(), reason=f"{MODEL_FILENAME} not found - copy it into models/"),
    pytest.mark.skipif(not PRE.exists() or json.loads(PRE.read_text()).get("_meta", {}).get("status") != STATUS_VERIFIED,
                       reason="models/preprocessing.json not generated yet - run scripts/export_preprocessing.py"),
]


@pytest.fixture(scope="module")
def real():
    return FraudModel.load(MODEL), FeatureBuilder.from_file(PRE)


def test_real_model_threshold_and_feature_order(real):
    model, builder = real
    assert model.features == FEATURES == builder.features
    assert model.threshold == pytest.approx(0.9083510041236877, abs=1e-9), "artifact threshold differs from the documented value"


def test_real_model_scores_known_dataset_rows(real):
    """Rows 3-4 of the notebook's df.head(): a TRANSFER and a CASH_OUT that were labelled fraud, and a PAYMENT that was not."""
    model, builder = real
    cases = [  # type, amount, step, old_orig, new_orig, old_dest, new_dest, label
        ("TRANSFER", 181.0, 1, 181.0, 0.0, 0.0, 0.0, 1),
        ("CASH_OUT", 181.0, 1, 181.0, 0.0, 21182.0, 0.0, 1),
        ("PAYMENT", 9839.64, 1, 170136.0, 160296.36, 0.0, 0.0, 0),
    ]
    X = builder.build_many(type_codes=[c[0] for c in cases], amounts=[c[1] for c in cases], steps=[c[2] for c in cases],
                           balance_diff_orig=[c[3] - c[4] for c in cases], balance_diff_dest=[c[6] - c[5] for c in cases])
    p = model.predict_proba_many(X)
    assert all(0 <= v <= 1 and math.isfinite(v) for v in p)
    assert p[0] >= model.threshold and p[1] >= model.threshold, f"known frauds not flagged: {p}"
    assert p[2] < 0.5, f"ordinary payment scored as risky: {p}"
