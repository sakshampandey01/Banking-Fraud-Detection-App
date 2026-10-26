"""Feature generation, feature order, type encoding and preprocessing validation (SYNTHETIC inputs)."""
import json
import math
from pathlib import Path

import numpy as np
import pytest

from app.ml.features import (DEFAULT_TYPE_ENCODING, FEATURES, NOTEBOOK_NIGHT_HOURS, FeatureBuilder,
                             PreprocessingNotReady, engineer_features)
from conftest import verified_config

ROOT = Path(__file__).resolve().parent.parent


def identity_config(p99=1000.0):
    """center 0 / scale 1 so the scaled output equals the raw features."""
    c = verified_config(p99)
    c["scaler_center"], c["scaler_scale"] = [0.0] * 9, [1.0] * 9
    return c


def test_feature_order_is_the_models_training_order():
    assert FEATURES == ["step", "amount", "log_amount", "is_high_amount", "hour", "is_night",
                        "balance_diff_orig", "balance_diff_dest", "type_enc"]
    row = FeatureBuilder(identity_config()).build(type_code="TRANSFER", amount=5.0, step=3,
                                                  balance_diff_orig=5.0, balance_diff_dest=5.0)
    assert list(row.columns) == FEATURES and row.shape == (1, 9)


def test_formulas_match_the_notebook():
    row = FeatureBuilder(identity_config(p99=1000.0)).build(
        type_code="CASH_OUT", amount=181.0, step=27, balance_diff_orig=181.0, balance_diff_dest=-5.0).iloc[0]
    assert row["step"] == 27 and row["amount"] == 181.0
    assert row["log_amount"] == pytest.approx(math.log1p(181.0))
    assert row["hour"] == 3 and row["is_night"] == 1            # 27 % 24 = 3
    assert row["is_high_amount"] == 0
    assert row["balance_diff_orig"] == 181.0 and row["balance_diff_dest"] == -5.0
    assert row["type_enc"] == 1                                  # CASH_OUT


@pytest.mark.parametrize("hour,night", [(0, 1), (5, 1), (6, 0), (12, 0), (21, 0), (22, 1), (23, 1)])
def test_is_night_uses_notebook_definition_including_22_and_23(hour, night):
    out = engineer_features(step=24 * 5 + hour, amount=1.0, balance_diff_orig=0, balance_diff_dest=0,
                            type_enc=0, p99_amount=10.0)
    assert out["hour"][0] == hour and out["is_night"][0] == night
    assert NOTEBOOK_NIGHT_HOURS == (0, 1, 2, 3, 4, 5, 22, 23)


def test_step_24_is_hour_zero_and_night():
    out = engineer_features(step=24, amount=1.0, balance_diff_orig=0, balance_diff_dest=0, type_enc=0, p99_amount=10.0)
    assert out["hour"][0] == 0 and out["is_night"][0] == 1


def test_high_amount_is_strictly_greater_than_p99():
    f = lambda a: engineer_features(step=1, amount=a, balance_diff_orig=0, balance_diff_dest=0, type_enc=0, p99_amount=1000.0)["is_high_amount"][0]
    assert (f(999.99), f(1000.0), f(1000.01)) == (0, 0, 1)


def test_scaling_is_robust_scaler_formula():
    cfg = verified_config()
    raw = FeatureBuilder(identity_config(cfg["p99_amount"])).build(type_code="PAYMENT", amount=9839.64, step=1,
                                                                   balance_diff_orig=9839.64, balance_diff_dest=0.0)
    scaled = FeatureBuilder(cfg).build(type_code="PAYMENT", amount=9839.64, step=1,
                                       balance_diff_orig=9839.64, balance_diff_dest=0.0)
    expected = (raw.to_numpy() - np.array(cfg["scaler_center"])) / np.array(cfg["scaler_scale"])
    np.testing.assert_allclose(scaled.to_numpy(), expected)


def test_single_and_batch_building_agree():
    fb = FeatureBuilder(verified_config())
    rows = [("TRANSFER", 181.0, 1, 181.0, 0.0), ("PAYMENT", 9839.64, 26, 9839.64, 0.0), ("CASH_IN", 5e5, 743, -5e5, -5e5)]
    batch = fb.build_many(type_codes=[r[0] for r in rows], amounts=[r[1] for r in rows], steps=[r[2] for r in rows],
                          balance_diff_orig=[r[3] for r in rows], balance_diff_dest=[r[4] for r in rows])
    for i, r in enumerate(rows):
        one = fb.build(type_code=r[0], amount=r[1], step=r[2], balance_diff_orig=r[3], balance_diff_dest=r[4])
        np.testing.assert_array_equal(batch.iloc[[i]].to_numpy(), one.to_numpy())


def test_type_encoding_is_alphabetical_labelencoder_order():
    assert DEFAULT_TYPE_ENCODING == {"CASH_IN": 0, "CASH_OUT": 1, "DEBIT": 2, "PAYMENT": 3, "TRANSFER": 4}
    assert list(DEFAULT_TYPE_ENCODING) == sorted(DEFAULT_TYPE_ENCODING)
    fb = FeatureBuilder(verified_config())
    assert [fb.encode_type(t) for t in DEFAULT_TYPE_ENCODING] == [0, 1, 2, 3, 4]


def test_unknown_type_is_rejected():
    with pytest.raises(ValueError, match="Unknown transaction type"):
        FeatureBuilder(verified_config()).encode_type("REFUND")


def test_sql_seed_matches_model_encoding():
    """sql/02_seed_reference.sql must agree with the encoding the model was trained with."""
    import re
    sql = (ROOT / "sql" / "02_seed_reference.sql").read_text()
    seeded = {m.group(1): int(m.group(2)) for m in re.finditer(r"\('([A-Z_]+)',\s*(\d+),", sql)}
    assert seeded == DEFAULT_TYPE_ENCODING
    assert json.loads((ROOT / "models" / "preprocessing.json").read_text())["type_encoding"] == DEFAULT_TYPE_ENCODING


@pytest.mark.parametrize("mutate,match", [
    (lambda c: c.update(features=list(reversed(FEATURES))), "features"),
    (lambda c: c.update(p99_amount=None), "p99_amount"),
    (lambda c: c.update(p99_amount=0), "p99_amount"),
    (lambda c: c.update(p99_amount=float("nan")), "p99_amount"),
    (lambda c: c.update(type_encoding={}), "type_encoding"),
    (lambda c: c.update(type_encoding={"A": 1, "B": 2}), "codes must be"),
    (lambda c: c.update(night_hours=[]), "night_hours"),
    (lambda c: c.update(night_hours=[0, 24]), "night_hours"),
    (lambda c: c.update(scaler_center=None), "scaler_center"),
    (lambda c: c.update(scaler_center=[0.0] * 8), "scaler_center"),
    (lambda c: c.update(scaler_scale=[1.0] * 8 + [0.0]), "scaler_scale"),
    (lambda c: c.update(scaler_scale=None), "scaler_scale"),
])
def test_invalid_preprocessing_is_rejected(mutate, match):
    cfg = verified_config()
    mutate(cfg)
    with pytest.raises(PreprocessingNotReady, match=match):
        FeatureBuilder(cfg)


def test_unverified_config_is_refused_for_serving():
    cfg = verified_config()
    cfg["_meta"] = {"status": "PENDING_RUN_EXPORT_SCRIPT"}
    with pytest.raises(PreprocessingNotReady, match="export_preprocessing"):
        FeatureBuilder(cfg)
    FeatureBuilder(cfg, require_verified=False)          # structure is fine, only the status differs


def test_shipped_preprocessing_json_is_pending_and_never_scores():
    """The repository copy intentionally contains no invented numbers until export_preprocessing.py has run."""
    path = ROOT / "models" / "preprocessing.json"
    cfg = json.loads(path.read_text())
    if cfg["_meta"]["status"] == "VERIFIED_FROM_DATASET":
        FeatureBuilder.from_file(path)                    # the user already ran the script: it must be valid
    else:
        assert cfg["p99_amount"] is None and cfg["scaler_center"] is None and cfg["scaler_scale"] is None
        with pytest.raises(PreprocessingNotReady):
            FeatureBuilder.from_file(path)


def test_missing_and_corrupt_files(tmp_path):
    with pytest.raises(PreprocessingNotReady, match="not found"):
        FeatureBuilder.from_file(tmp_path / "nope.json")
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    with pytest.raises(PreprocessingNotReady, match="not valid JSON"):
        FeatureBuilder.from_file(bad)
