"""
Feature engineering shared by the live API and by scripts/export_preprocessing.py.

It reproduces, step by step, the pipeline in Analysis.ipynb:

  cell 9   log_amount        = log1p(amount)
           is_high_amount    = amount > df['amount'].quantile(0.99)       (strict >, whole dataset)
  cell 14  hour              = step % 24
           is_night          = hour in [0, 1, 2, 3, 4, 5, 22, 23]
  cell 18  balance_diff_orig = oldbalanceOrg  - newbalanceOrig
           balance_diff_dest = newbalanceDest - oldbalanceDest
  cell 19  type_enc          = LabelEncoder().fit_transform(type)         (alphabetical)
  cell 21  train_test_split(test_size=0.2, stratify=y, random_state=42)
           RobustScaler fitted on the TRAIN split, applied to all 9 columns
  cell 36  model.predict_proba(X[features])  with features in the order of X's columns

Keeping ONE implementation of the formulas (``engineer_features``) for both training-time
statistics and serving is what guarantees train/serve parity.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

# The column order the model was trained with (X_train.columns in the notebook).
FEATURES: list[str] = [
    "step",
    "amount",
    "log_amount",
    "is_high_amount",
    "hour",
    "is_night",
    "balance_diff_orig",
    "balance_diff_dest",
    "type_enc",
]

# Notebook cell 14: df['hour'].isin([0,1,2,3,4,5,22,23])
NOTEBOOK_NIGHT_HOURS: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 22, 23)

# Notebook cell 19: LabelEncoder sorts the class names alphabetically. PaySim has exactly
# these five transaction types. scripts/export_preprocessing.py re-derives this from the
# real dataset and refuses to continue if it ever differs.
DEFAULT_TYPE_ENCODING: dict[str, int] = {
    "CASH_IN": 0,
    "CASH_OUT": 1,
    "DEBIT": 2,
    "PAYMENT": 3,
    "TRANSFER": 4,
}

STATUS_VERIFIED = "VERIFIED_FROM_DATASET"


class PreprocessingNotReady(RuntimeError):
    """preprocessing.json still holds placeholders or is inconsistent."""


def engineer_features(
    *,
    step: Any,
    amount: Any,
    balance_diff_orig: Any,
    balance_diff_dest: Any,
    type_enc: Any,
    p99_amount: float,
    night_hours: Sequence[int] = NOTEBOOK_NIGHT_HOURS,
) -> dict[str, np.ndarray]:
    """Raw (UNSCALED) feature columns as float64 arrays, keyed by feature name.

    Accepts scalars or array-likes. Pure function: no I/O, no global state.
    """
    step_a = np.atleast_1d(np.asarray(step, dtype=np.float64))
    amount_a = np.atleast_1d(np.asarray(amount, dtype=np.float64))
    hour = np.mod(step_a, 24)
    return {
        "step": step_a,
        "amount": amount_a,
        "log_amount": np.log1p(amount_a),
        "is_high_amount": (amount_a > p99_amount).astype(np.float64),
        "hour": hour,
        "is_night": np.isin(hour, np.asarray(night_hours, dtype=np.float64)).astype(np.float64),
        "balance_diff_orig": np.atleast_1d(np.asarray(balance_diff_orig, dtype=np.float64)),
        "balance_diff_dest": np.atleast_1d(np.asarray(balance_diff_dest, dtype=np.float64)),
        "type_enc": np.atleast_1d(np.asarray(type_enc, dtype=np.float64)),
    }


def _is_number_list(value: Any, length: int) -> bool:
    return (
        isinstance(value, list)
        and len(value) == length
        and all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in value)
    )


class FeatureBuilder:
    """Turns transactions into the scaled feature matrix the saved model expects."""

    def __init__(self, config: Mapping[str, Any], *, require_verified: bool = True):
        self.config = dict(config)
        self._validate(require_verified)
        self.features: list[str] = list(self.config["features"])
        self.p99_amount: float = float(self.config["p99_amount"])
        self.night_hours: tuple[int, ...] = tuple(int(h) for h in self.config["night_hours"])
        self.type_encoding: dict[str, int] = {k: int(v) for k, v in self.config["type_encoding"].items()}
        self._center = np.asarray(self.config["scaler_center"], dtype=np.float64)
        self._scale = np.asarray(self.config["scaler_scale"], dtype=np.float64)

    # ------------------------------------------------------------------ loading
    @classmethod
    def from_file(cls, path: str | Path, *, require_verified: bool = True) -> "FeatureBuilder":
        p = Path(path)
        if not p.exists():
            raise PreprocessingNotReady(
                f"Preprocessing file not found: {p}. Run `python scripts/export_preprocessing.py` "
                "on the machine that has Fraud.csv."
            )
        try:
            cfg = json.loads(p.read_text())
        except json.JSONDecodeError as exc:
            raise PreprocessingNotReady(f"{p} is not valid JSON: {exc}") from exc
        return cls(cfg, require_verified=require_verified)

    # --------------------------------------------------------------- validation
    def _validate(self, require_verified: bool) -> None:
        cfg = self.config
        n = len(FEATURES)

        if cfg.get("features") != FEATURES:
            raise PreprocessingNotReady(f"'features' must equal {FEATURES} (the model's training order), got {cfg.get('features')}")

        if require_verified:
            status = (cfg.get("_meta") or {}).get("status")
            if status != STATUS_VERIFIED:
                raise PreprocessingNotReady(
                    "models/preprocessing.json has not been generated from the real dataset yet "
                    f"(status={status!r}). Run `python scripts/export_preprocessing.py` on the Mac "
                    "that holds Fraud.csv. Refusing to score with placeholder values."
                )

        p99 = cfg.get("p99_amount")
        if not isinstance(p99, (int, float)) or isinstance(p99, bool) or not math.isfinite(p99) or p99 <= 0:
            raise PreprocessingNotReady(f"'p99_amount' must be a positive number, got {p99!r}")

        hours = cfg.get("night_hours")
        if not (isinstance(hours, list) and hours and all(isinstance(h, int) and 0 <= h <= 23 for h in hours)):
            raise PreprocessingNotReady(f"'night_hours' must be a list of hours 0..23, got {hours!r}")

        enc = cfg.get("type_encoding")
        if not (isinstance(enc, dict) and enc and all(isinstance(v, int) for v in enc.values())):
            raise PreprocessingNotReady(f"'type_encoding' must map type names to integers, got {enc!r}")
        if sorted(enc.values()) != list(range(len(enc))):
            raise PreprocessingNotReady(f"'type_encoding' codes must be 0..{len(enc) - 1}, got {enc!r}")

        if not _is_number_list(cfg.get("scaler_center"), n):
            raise PreprocessingNotReady(f"'scaler_center' must be {n} finite numbers, got {cfg.get('scaler_center')!r}")
        if not _is_number_list(cfg.get("scaler_scale"), n) or any(v <= 0 for v in cfg["scaler_scale"]):
            raise PreprocessingNotReady(f"'scaler_scale' must be {n} finite positive numbers, got {cfg.get('scaler_scale')!r}")

    # ------------------------------------------------------------------ building
    def encode_type(self, type_code: str) -> int:
        try:
            return self.type_encoding[type_code]
        except KeyError:
            raise ValueError(f"Unknown transaction type {type_code!r}; expected one of {sorted(self.type_encoding)}") from None

    def build_many(
        self,
        *,
        type_codes: Sequence[str],
        amounts: Sequence[float],
        steps: Sequence[int],
        balance_diff_orig: Sequence[float],
        balance_diff_dest: Sequence[float],
    ) -> pd.DataFrame:
        """Vectorised: scaled feature matrix (one row per transaction), columns in model order."""
        raw = engineer_features(
            step=steps,
            amount=amounts,
            balance_diff_orig=balance_diff_orig,
            balance_diff_dest=balance_diff_dest,
            type_enc=[self.encode_type(t) for t in type_codes],
            p99_amount=self.p99_amount,
            night_hours=self.night_hours,
        )
        matrix = np.column_stack([raw[name] for name in self.features])
        scaled = (matrix - self._center) / self._scale          # RobustScaler.transform
        # DataFrame with column names: XGBoost validates feature names/order
        return pd.DataFrame(scaled, columns=self.features)

    def build(self, *, type_code: str, amount: float, step: int,
              balance_diff_orig: float, balance_diff_dest: float) -> pd.DataFrame:
        """One transaction -> a one-row scaled DataFrame."""
        return self.build_many(
            type_codes=[type_code], amounts=[amount], steps=[step],
            balance_diff_orig=[balance_diff_orig], balance_diff_dest=[balance_diff_dest],
        )
