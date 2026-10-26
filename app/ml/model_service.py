"""Loads the pickled artifact ONCE at startup and exposes a small predict API.

Expected artifact (written by Analysis.ipynb cell 36 with joblib.dump):

    {"model_name": "XGBoost", "model": <fitted estimator with predict_proba>,
     "threshold": 0.9083510041236877, "features": [...9 names in training order...]}
"""
from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import pandas as pd


class ModelUnavailable(RuntimeError):
    """The model artifact is missing or unusable. The message tells the user how to fix it."""


def classify_risk(probability: float, high_threshold: float, medium_threshold: float) -> str:
    """HIGH if p >= model threshold, MEDIUM if p >= medium threshold, else LOW.

    Both sides are rounded to 6 decimals first so the answer is identical to the database
    stored procedure, which compares the NUMERIC(7,6) values it is given.
    """
    p, hi, med = round(probability, 6), round(high_threshold, 6), round(medium_threshold, 6)
    if p >= hi:
        return "HIGH"
    if p >= med:
        return "MEDIUM"
    return "LOW"


@dataclass
class FraudModel:
    name: str
    threshold: float
    features: list[str]
    _model: Any

    @classmethod
    def load(cls, path: str | Path) -> "FraudModel":
        p = Path(path)
        if not p.exists():
            raise ModelUnavailable(
                f"Model file not found: {p}. Copy best_fraud_model_tuned.pkl (created by cell 36 of "
                "Analysis.ipynb) into the project's models/ folder, or set MODEL_PATH in .env."
            )
        try:
            # Silences XGBoost's "serialized with an older version" notice; see README for pinning advice.
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                artifact = joblib.load(p)
        except ModuleNotFoundError as exc:
            raise ModelUnavailable(
                f"Could not unpickle {p.name}: missing Python package '{exc.name}'. "
                "Install requirements.txt in the active virtual environment (xgboost is required)."
            ) from exc
        except Exception as exc:  # corrupt file, incompatible library versions, ...
            raise ModelUnavailable(
                f"Could not load {p.name}: {type(exc).__name__}: {exc}. If xgboost/scikit-learn versions "
                "differ from the notebook environment, install the versions used for training."
            ) from exc

        if not isinstance(artifact, dict):
            raise ModelUnavailable(f"{p.name} must contain a dict with model/threshold/features, got {type(artifact).__name__}")
        missing = {"model", "threshold", "features"} - set(artifact)
        if missing:
            raise ModelUnavailable(f"Model artifact is missing keys: {sorted(missing)}")
        if not hasattr(artifact["model"], "predict_proba"):
            raise ModelUnavailable("artifact['model'] has no predict_proba()")

        threshold = float(artifact["threshold"])
        if not (math.isfinite(threshold) and 0.0 < threshold < 1.0):
            raise ModelUnavailable(f"Invalid decision threshold in artifact: {artifact['threshold']!r}")

        return cls(
            name=str(artifact.get("model_name", type(artifact["model"]).__name__)),
            threshold=threshold,
            features=list(artifact["features"]),
            _model=artifact["model"],
        )

    def predict_proba_many(self, X: pd.DataFrame) -> list[float]:
        """Fraud probability (class 1) for every row of X."""
        proba = self._model.predict_proba(X[self.features])
        return [float(v) for v in proba[:, 1]]

    def predict_proba(self, X: pd.DataFrame) -> float:
        """Probability that the (single-row) transaction is fraud."""
        return self.predict_proba_many(X)[0]
