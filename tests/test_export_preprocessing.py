"""scripts/export_preprocessing.py must reproduce the notebook's preprocessing exactly.

SYNTHETIC DATA ONLY: these tests prove the script is a faithful replay of the notebook code
on a small generated CSV. They say nothing about the real 6.36M-row dataset - the script prints
its own cross-check against the notebook's real numbers when you run it on your Mac.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, RobustScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import export_preprocessing as exp  # noqa: E402

from app.ml.features import FEATURES, STATUS_VERIFIED, FeatureBuilder  # noqa: E402


def notebook_replica(csv: Path) -> dict:
    """Analysis.ipynb cells 2, 9, 14, 18, 19, 21 - copied as literally as possible."""
    df = pd.read_csv(csv)                                                   # cell 2
    df["log_amount"] = np.log1p(df["amount"])                               # cell 9
    p99 = df["amount"].quantile(0.99)
    df["is_high_amount"] = (df["amount"] > p99).astype(int)
    df["hour"] = df["step"] % 24                                            # cell 14
    df["is_night"] = df["hour"].isin([0, 1, 2, 3, 4, 5, 22, 23]).astype(int)
    df["balance_diff_orig"] = df["oldbalanceOrg"] - df["newbalanceOrig"]    # cell 18
    df["balance_diff_dest"] = df["newbalanceDest"] - df["oldbalanceDest"]
    df = df.drop(columns=["oldbalanceOrg", "newbalanceOrig", "oldbalanceDest", "newbalanceDest"])
    df.fillna(0, inplace=True)                                              # cell 19
    le = LabelEncoder()
    df["type_enc"] = le.fit_transform(df["type"])
    df.drop(["nameOrig", "nameDest", "type"], axis=1, inplace=True)
    X = df.drop(columns=["isFraud", "isFlaggedFraud"])                      # cell 21
    y = df["isFraud"].values
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    scaler = RobustScaler()
    num_cols = X_train.select_dtypes(include=[np.number]).columns
    scaler.fit(X_train[num_cols])
    return {"columns": list(X.columns), "p99": p99, "classes": list(le.classes_),
            "center": scaler.center_, "scale": scaler.scale_,
            "X_test_scaled": scaler.transform(X_test[num_cols]), "test_index": X_test.index.to_numpy()}


@pytest.fixture(scope="module")
def result(tmp_path_factory, paysim_csv):
    out = tmp_path_factory.mktemp("out") / "preprocessing.json"
    config = exp.run(paysim_csv, out, check_model=False, expected=None, say=lambda m: None)
    return config, out


def test_notebook_column_order_equals_project_feature_order(paysim_csv):
    assert notebook_replica(paysim_csv)["columns"] == FEATURES


def test_p99_identical_to_notebook(result, paysim_csv):
    config, _ = result
    assert config["p99_amount"] == notebook_replica(paysim_csv)["p99"]


def test_type_encoding_identical_to_notebook(result, paysim_csv):
    config, _ = result
    classes = notebook_replica(paysim_csv)["classes"]
    assert config["type_encoding"] == {c: i for i, c in enumerate(classes)}


def test_scaler_identical_to_notebook(result, paysim_csv):
    config, _ = result
    ref = notebook_replica(paysim_csv)
    np.testing.assert_array_equal(config["scaler_center"], ref["center"])
    np.testing.assert_array_equal(config["scaler_scale"], ref["scale"])


def test_serving_features_equal_notebook_scaled_test_matrix(result, paysim_csv):
    """Train/serve parity: FeatureBuilder on raw rows == the notebook's scaled X_test."""
    config, _ = result
    ref = notebook_replica(paysim_csv)
    raw = pd.read_csv(paysim_csv).loc[ref["test_index"]]
    built = FeatureBuilder(config).build_many(
        type_codes=raw["type"].tolist(),
        amounts=raw["amount"].to_numpy(),
        steps=raw["step"].to_numpy(),
        balance_diff_orig=(raw["oldbalanceOrg"] - raw["newbalanceOrig"]).to_numpy(),
        balance_diff_dest=(raw["newbalanceDest"] - raw["oldbalanceDest"]).to_numpy(),
    )
    assert list(built.columns) == FEATURES
    np.testing.assert_allclose(built.to_numpy(), ref["X_test_scaled"], rtol=0, atol=1e-12)


def test_written_json_is_verified_and_loadable(result):
    config, out = result
    on_disk = json.loads(out.read_text())
    assert on_disk["_meta"]["status"] == STATUS_VERIFIED
    assert on_disk["night_hours"] == [0, 1, 2, 3, 4, 5, 22, 23]
    FeatureBuilder.from_file(out)                   # passes full validation, require_verified=True


def test_second_run_backs_up_existing_file(tmp_path, paysim_csv):
    out = tmp_path / "preprocessing.json"
    out.write_text('{"keep": "me"}')
    exp.run(paysim_csv, out, check_model=False, expected=None, say=lambda m: None)
    backups = list(tmp_path.glob("preprocessing.json.bak-*"))
    assert len(backups) == 1 and json.loads(backups[0].read_text()) == {"keep": "me"}
    assert not list(tmp_path.glob("*.tmp"))


def test_missing_csv_gives_friendly_error(tmp_path):
    with pytest.raises(exp.ExportError, match="Dataset not found"):
        exp.compute(tmp_path / "nope.csv", expected=None, say=lambda m: None)


def test_missing_column_gives_friendly_error(tmp_path):
    bad = tmp_path / "bad.csv"
    pd.DataFrame({"step": [1], "type": ["PAYMENT"]}).to_csv(bad, index=False)
    with pytest.raises(exp.ExportError, match="missing columns"):
        exp.compute(bad, expected=None, say=lambda m: None)


def test_unexpected_transaction_types_are_rejected(tmp_path, paysim_csv):
    df = pd.read_csv(paysim_csv)
    df.loc[df["type"] == "DEBIT", "type"] = "AAA_NEW_TYPE"      # sorts first -> codes shift
    bad = tmp_path / "bad_types.csv"
    df.to_csv(bad, index=False)
    with pytest.raises(exp.ExportError, match="assumes"):
        exp.compute(bad, expected=None, say=lambda m: None)


def test_cross_check_flags_differences_without_failing(paysim_csv):
    lines: list[str] = []
    config, _ = exp.compute(paysim_csv, say=lines.append)       # default expected = REAL notebook numbers
    assert any("DIFFERS rows" in line for line in lines)       # synthetic file is not 6,362,620 rows
    assert config["_meta"]["notebook_crosscheck"]["rows"]["match"] is False


def test_main_returns_error_code_for_missing_file(tmp_path, capsys):
    code = exp.main(["--csv", str(tmp_path / "missing.csv"), "--out", str(tmp_path / "o.json")])
    assert code == 2
    assert "Dataset not found" in capsys.readouterr().err


# --------------------------------------------------------------- optional model check
def test_model_check_runs_with_synthetic_artifact(tmp_path, paysim_csv):
    """Exercises verify_model() with a SYNTHETIC sklearn artifact (not the real XGBoost model)."""
    from conftest import synthetic_artifact
    art = synthetic_artifact(tmp_path / "m.pkl", threshold=0.30)
    out = tmp_path / "preprocessing.json"
    config = exp.run(paysim_csv, out, model_path=art, expected=None, say=lambda m: None)
    check = config["_meta"]["model_check"]
    c = check["confusion"]
    assert c["tp"] + c["fn"] + c["fp"] + c["tn"] == int(len(pd.read_csv(paysim_csv)) * 0.2 + 0.999)  # ceil(0.2n)
    assert check["feature_order_matches"] is True
    assert check["threshold_matches_configured"] is False       # 0.30 is not the documented 0.90835...
    assert 0.0 <= check["recall"] <= 1.0
    assert json.loads(out.read_text())["_meta"]["model_check"]["model_name"] == "SYNTHETIC-TEST-MODEL"


def test_model_check_survives_a_model_with_no_positive_predictions(tmp_path, paysim_csv, artifact_path):
    """Regression: the default synthetic model never reaches 0.908 -> precision is undefined, must not crash."""
    config = exp.run(paysim_csv, tmp_path / "o.json", model_path=artifact_path, expected=None, say=lambda m: None)
    check = config["_meta"]["model_check"]
    assert check["confusion"]["tp"] == 0 and check["precision"] is None
    assert check["threshold_matches_configured"] is True


def test_model_with_wrong_feature_order_is_rejected(tmp_path, paysim_csv):
    import joblib
    from sklearn.dummy import DummyClassifier
    bad = tmp_path / "bad.pkl"
    joblib.dump({"model": DummyClassifier().fit([[0]] * 4, [0, 1, 0, 1]), "threshold": 0.9,
                 "features": list(reversed(FEATURES))}, bad)
    with pytest.raises(exp.ExportError, match="differs from the project"):
        exp.run(paysim_csv, tmp_path / "o.json", model_path=bad, expected=None, say=lambda m: None)


def test_explicit_missing_model_path_is_an_error(tmp_path, paysim_csv):
    with pytest.raises(exp.ExportError, match="--model file not found"):
        exp.run(paysim_csv, tmp_path / "o.json", model_path=tmp_path / "nope.pkl", expected=None, say=lambda m: None)
