"""
Re-creates the preprocessing parameters your notebook fitted but never saved.

WHY: best_fraud_model_tuned.pkl contains {model_name, model, threshold, features}.
The model was trained on RobustScaler-scaled features, but the scaler itself was not
saved. Everything the scaler needs (median + IQR per column), the 99th-percentile
amount cut-off and the type encoding are deterministic given the CSV and the notebook's
split (test_size=0.2, stratify=y, random_state=42), so we recompute them here and store
them as plain JSON (no sklearn pickle-version problems at serving time).

    python -m scripts.export_preprocessing --csv data/Fraud.csv
"""
import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, RobustScaler


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--model", default="models/best_fraud_model_tuned.pkl")
    ap.add_argument("--out", default="models/preprocessing.json")
    args = ap.parse_args()

    artifact = joblib.load(args.model)
    features = artifact["features"]

    df = pd.read_csv(args.csv)

    # --- exactly the notebook's feature engineering -------------------------
    df["log_amount"] = np.log1p(df["amount"])
    p99 = float(df["amount"].quantile(0.99))
    df["is_high_amount"] = (df["amount"] > p99).astype(int)
    df["hour"] = df["step"] % 24
    df["is_night"] = df["hour"].isin([0, 1, 2, 3, 4, 5, 22, 23]).astype(int)
    df["balance_diff_orig"] = df["oldbalanceOrg"] - df["newbalanceOrig"]
    df["balance_diff_dest"] = df["newbalanceDest"] - df["oldbalanceDest"]
    le = LabelEncoder()
    df["type_enc"] = le.fit_transform(df["type"])

    X, y = df[features], df["isFraud"].values
    X_train, _, _, _ = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

    scaler = RobustScaler().fit(X_train)        # all 9 features are numeric
    out = {
        "features": features,
        "p99_amount": p99,
        "night_hours": [0, 1, 2, 3, 4, 5, 22, 23],
        "type_encoding": {c: int(i) for i, c in enumerate(le.classes_)},
        "scaler_center": [float(v) for v in scaler.center_],
        "scaler_scale": [float(v) for v in scaler.scale_],
    }
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(f"wrote {args.out}")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
