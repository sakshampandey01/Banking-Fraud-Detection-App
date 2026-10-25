"""Loads the pickled artifact ONCE at startup and exposes a tiny predict() API."""
import warnings
from dataclasses import dataclass

import joblib
import pandas as pd


@dataclass
class FraudModel:
    name: str
    threshold: float
    features: list[str]
    _model: object

    @classmethod
    def load(cls, path: str) -> "FraudModel":
        # Silences XGBoost's "serialized with an older version" notice; see README for pinning advice.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            artifact = joblib.load(path)

        missing = {"model", "threshold", "features"} - set(artifact)
        if missing:
            raise RuntimeError(f"Model artifact is missing keys: {missing}")

        return cls(
            name=str(artifact.get("model_name", type(artifact["model"]).__name__)),
            threshold=float(artifact["threshold"]),
            features=list(artifact["features"]),
            _model=artifact["model"],
        )

    def predict_proba(self, X: pd.DataFrame) -> float:
        """Probability that the transaction is fraud (class 1)."""
        return float(self._model.predict_proba(X[self.features])[0, 1])
