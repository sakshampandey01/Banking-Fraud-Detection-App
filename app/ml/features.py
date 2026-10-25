"""
Rebuilds the exact feature vector your notebook trained on, for ONE live transaction.

Notebook pipeline (see Analysis.ipynb):
  log_amount, is_high_amount (amount > 99th pct), hour = step % 24, is_night,
  balance_diff_orig = old - new (origin), balance_diff_dest = new - old (dest),
  type_enc (LabelEncoder) -> RobustScaler on all 9 columns -> XGBoost.
The scaler was never saved, so scripts/export_preprocessing.py recomputed it into
models/preprocessing.json. Scaling here is (x - center) / scale, i.e. RobustScaler.
"""
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


class FeatureBuilder:
    def __init__(self, preprocessing_path: str):
        cfg = json.loads(Path(preprocessing_path).read_text())
        self.features: list[str] = cfg["features"]
        self.p99_amount: float = cfg["p99_amount"]
        self.night_hours = set(cfg["night_hours"])
        self.type_encoding: dict[str, int] = cfg["type_encoding"]
        self._center = np.array(cfg["scaler_center"], dtype=float)
        self._scale = np.array(cfg["scaler_scale"], dtype=float)
        self._scale[self._scale == 0] = 1.0           # same guard sklearn applies

    def build(self, *, type_code: str, amount: float, step: int,
              balance_diff_orig: float, balance_diff_dest: float) -> pd.DataFrame:
        hour = step % 24
        raw = {
            "step": step,
            "amount": amount,
            "log_amount": math.log1p(amount),
            "is_high_amount": int(amount > self.p99_amount),
            "hour": hour,
            "is_night": int(hour in self.night_hours),
            "balance_diff_orig": balance_diff_orig,
            "balance_diff_dest": balance_diff_dest,
            "type_enc": self.type_encoding[type_code],
        }
        row = np.array([[raw[name] for name in self.features]], dtype=float)
        scaled = (row - self._center) / self._scale
        # DataFrame with column names: XGBoost validates feature names/order
        return pd.DataFrame(scaled, columns=self.features)
