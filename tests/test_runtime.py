"""Start-up readiness logic: the server must degrade with clear messages, never crash (SYNTHETIC artifacts)."""
import json

import pytest

from app.ml.features import DEFAULT_TYPE_ENCODING
from app.runtime import DatabaseProblem, Runtime, ScoringUnavailable
from conftest import verified_config


@pytest.fixture()
def ready_files(tmp_path, artifact_path):
    pre = tmp_path / "preprocessing.json"
    pre.write_text(json.dumps(verified_config()))
    return pre, artifact_path


def test_everything_present_is_ready(ready_files):
    rt = Runtime(*ready_files)
    rt.load_artifacts()
    rt.verify_database(lambda: dict(DEFAULT_TYPE_ENCODING))
    assert rt.scoring_issues() == [] and rt.db_checked
    model, builder = rt.require_scoring(lambda: dict(DEFAULT_TYPE_ENCODING))
    assert model.features == builder.features


def test_missing_model_is_reported_with_instructions(tmp_path, ready_files):
    rt = Runtime(ready_files[0], tmp_path / "missing.pkl")
    rt.load_artifacts()
    assert [i.code for i in rt.model_issues()] == ["MODEL_UNAVAILABLE"]
    with pytest.raises(ScoringUnavailable) as e:
        rt.require_model()
    assert "models/" in e.value.issues[0].message


def test_placeholder_preprocessing_blocks_scoring(tmp_path, artifact_path):
    pre = tmp_path / "p.json"
    cfg = verified_config()
    cfg["_meta"] = {"status": "PENDING_RUN_EXPORT_SCRIPT"}
    cfg["p99_amount"] = None
    pre.write_text(json.dumps(cfg))
    rt = Runtime(pre, artifact_path)
    rt.load_artifacts()
    assert [i.code for i in rt.model_issues()] == ["PREPROCESSING_NOT_READY"]
    with pytest.raises(ScoringUnavailable):
        rt.require_model()


def test_both_artifacts_missing_reports_both(tmp_path):
    rt = Runtime(tmp_path / "a.json", tmp_path / "b.pkl")
    rt.load_artifacts()
    assert {i.code for i in rt.model_issues()} == {"PREPROCESSING_NOT_READY", "MODEL_UNAVAILABLE"}


def test_feature_mismatch_between_model_and_preprocessing(tmp_path, ready_files):
    import joblib
    from sklearn.dummy import DummyClassifier
    pkl = tmp_path / "other.pkl"
    joblib.dump({"model": DummyClassifier().fit([[0], [1]], [0, 1]), "threshold": 0.9,
                 "features": list(reversed(verified_config()["features"]))}, pkl)
    rt = Runtime(ready_files[0], pkl)
    rt.load_artifacts()
    assert "FEATURE_MISMATCH" in [i.code for i in rt.model_issues()]


def test_database_encoding_mismatch_blocks_scoring(ready_files):
    rt = Runtime(*ready_files)
    rt.load_artifacts()
    wrong = {**DEFAULT_TYPE_ENCODING, "TRANSFER": 0, "CASH_IN": 4}
    rt.verify_database(lambda: wrong)
    assert rt.db_issue.code == "DB_ENCODING_MISMATCH" and not rt.db_checked
    with pytest.raises(ScoringUnavailable, match="init_db"):
        rt.require_scoring(lambda: wrong)


def test_database_down_then_recovers_without_restart(ready_files):
    rt = Runtime(*ready_files)
    rt.load_artifacts()

    def down():
        raise DatabaseProblem("DB_UNAVAILABLE", "Cannot connect to PostgreSQL.")

    rt.verify_database(down)
    assert rt.db_issue.code == "DB_UNAVAILABLE"
    with pytest.raises(ScoringUnavailable):
        rt.require_scoring(down)
    model, _ = rt.require_scoring(lambda: dict(DEFAULT_TYPE_ENCODING))      # database came back
    assert rt.db_checked and rt.db_issue is None and model is not None


def test_unexpected_exception_in_db_check_does_not_crash_startup(ready_files):
    rt = Runtime(*ready_files)
    rt.load_artifacts()
    rt.verify_database(lambda: 1 / 0)
    assert rt.db_issue.code == "DB_ERROR"
