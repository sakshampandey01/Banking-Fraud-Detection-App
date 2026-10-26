#!/usr/bin/env python3
"""
Recover models/preprocessing.json from the FULL dataset by replaying Analysis.ipynb.

What it recomputes (nothing is guessed):
  * p99_amount        df['amount'].quantile(0.99)                       (notebook cell 9, all rows)
  * type_encoding     LabelEncoder().fit_transform(type)                (cell 19)
  * scaler_center/    RobustScaler().fit(X_train) on the 9 features     (cell 21)
    scaler_scale      with train_test_split(test_size=0.2, stratify=y, random_state=42)

It also:
  * cross-checks the dataset against the numbers printed in the notebook
    (6,362,620 rows, 8,213 frauds, 63,627 rows above p99, 1,272,524 test rows ...),
  * prints the observed balance effect of each transaction type, so you can confirm the
    reference data in sql/02_seed_reference.sql,
  * if best_fraud_model_tuned.pkl is found, loads it and checks that the rebuilt preprocessing
    reproduces the notebook's test-set results (TP 1474 / FN 169 / FP 3612 / TN 1267269).

Usage (from the project folder, with the virtual environment active):

    python scripts/export_preprocessing.py
    python scripts/export_preprocessing.py --csv /path/to/Fraud.csv
    python scripts/export_preprocessing.py --skip-model-check

Memory/time: measured at about 1.2 GB peak and ~10 s on a 6.36M-row file (only the 8 needed
columns are read). Needs a machine with at least 4 GB of free RAM; add --skip-model-check to save a little more.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, RobustScaler

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.ml.features import (  # noqa: E402  (needs ROOT on sys.path)
    DEFAULT_TYPE_ENCODING,
    FEATURES,
    NOTEBOOK_NIGHT_HOURS,
    STATUS_VERIFIED,
    FeatureBuilder,
    engineer_features,
)

DEFAULT_CSV = Path.home() / "Desktop" / "Bank-Fraud-Detection" / "Fraud.csv"
FALLBACK_CSV = ROOT / "Fraud.csv"
DEFAULT_OUT = ROOT / "models" / "preprocessing.json"
MODEL_CANDIDATES = [ROOT / "models" / "best_fraud_model_tuned.pkl", ROOT / "best_fraud_model_tuned.pkl"]

TEST_SIZE = 0.2
RANDOM_STATE = 42
P99_QUANTILE = 0.99
CONFIGURED_THRESHOLD = 0.9083510041236877      # value quoted for the saved artifact

REQUIRED_COLUMNS = ["step", "type", "amount", "oldbalanceOrg", "newbalanceOrig",
                    "oldbalanceDest", "newbalanceDest", "isFraud"]

# Numbers printed by Analysis.ipynb for the original full dataset.
NOTEBOOK_EXPECTED = {
    "rows": 6_362_620,            # cell 3
    "fraud_rows": 8_213,          # cell 3
    "above_p99": 63_627,          # cell 9
    "test_rows": 1_272_524,       # cell 24
    "test_fraud_rows": 1_643,     # cell 24 (support of class 1)
    "confusion": {"tp": 1474, "fn": 169, "fp": 3612, "tn": 1_267_269},   # cell 38
}

# Expected (origin_effect, dest_effect) per type = what sql/02_seed_reference.sql seeds.
# Origin/dest balance goes UP (+1) or DOWN (-1) by the amount.
EXPECTED_EFFECTS = {
    "CASH_IN": (+1, -1),
    "CASH_OUT": (-1, +1),
    "DEBIT": (-1, +1),
    "PAYMENT": (-1, +1),
    "TRANSFER": (-1, +1),
}


class ExportError(Exception):
    """A problem the user can fix; printed without a traceback."""


def _say(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _peak_memory_mb() -> float | None:
    try:
        import resource
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return rss / (1024 * 1024) if sys.platform == "darwin" else rss / 1024
    except Exception:
        return None


# ----------------------------------------------------------------------------- data
@dataclass
class Dataset:
    step: np.ndarray
    amount: np.ndarray
    old_o: np.ndarray
    new_o: np.ndarray
    old_d: np.ndarray
    new_d: np.ndarray
    type_codes: np.ndarray
    classes: list[str]
    y: np.ndarray

    @property
    def n(self) -> int:
        return len(self.y)


def load_dataset(csv_path: Path, say: Callable[[str], None]) -> Dataset:
    if not csv_path.exists():
        raise ExportError(
            f"Dataset not found: {csv_path}\n"
            f"  Expected it at {DEFAULT_CSV}\n"
            "  Put Fraud.csv there, or pass --csv /full/path/to/Fraud.csv"
        )
    header = pd.read_csv(csv_path, nrows=0).columns.tolist()
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        raise ExportError(f"{csv_path.name} is missing columns {missing}. Found: {header}")

    say(f"Reading {csv_path} ({csv_path.stat().st_size / 1e6:,.0f} MB) - only the {len(REQUIRED_COLUMNS)} needed columns ...")
    t0 = time.time()
    df = pd.read_csv(
        csv_path,
        usecols=REQUIRED_COLUMNS,
        dtype={"step": "int32", "type": "category", "amount": "float64",
               "oldbalanceOrg": "float64", "newbalanceOrig": "float64",
               "oldbalanceDest": "float64", "newbalanceDest": "float64", "isFraud": "int8"},
    )
    say(f"  read {len(df):,} rows in {time.time() - t0:,.1f}s")
    if df.empty:
        raise ExportError("The CSV has no rows.")

    numeric = [c for c in REQUIRED_COLUMNS if c != "type"]
    n_nan = int(df[numeric].isna().sum().sum())
    if n_nan or df["type"].isna().any():
        say(f"  WARNING: {n_nan:,} missing numeric values; filling with 0 exactly as the notebook did (cell 19)")
        df[numeric] = df[numeric].fillna(0)
    if df["type"].isna().any():
        raise ExportError("The 'type' column contains empty values; cannot encode.")
    if not set(np.unique(df["isFraud"].to_numpy())) <= {0, 1}:
        raise ExportError("isFraud must contain only 0/1.")

    # LabelEncoder = alphabetical class order (notebook cell 19)
    le = LabelEncoder().fit([str(c) for c in df["type"].cat.categories])
    classes = [str(c) for c in le.classes_]
    codes = df["type"].cat.set_categories(classes).cat.codes.to_numpy()
    if (codes < 0).any():
        raise ExportError("Internal error while encoding 'type'.")

    return Dataset(
        step=df["step"].to_numpy(), amount=df["amount"].to_numpy(),
        old_o=df["oldbalanceOrg"].to_numpy(), new_o=df["newbalanceOrig"].to_numpy(),
        old_d=df["oldbalanceDest"].to_numpy(), new_d=df["newbalanceDest"].to_numpy(),
        type_codes=codes, classes=classes, y=df["isFraud"].to_numpy(),
    )


# --------------------------------------------------------------------------- compute
@dataclass
class Context:
    """Everything the optional model check needs, kept out of the JSON."""
    raw: dict[str, np.ndarray]
    train_idx: np.ndarray
    test_idx: np.ndarray
    y: np.ndarray
    checks: dict = field(default_factory=dict)


def _check(label: str, actual, expected, say, checks: dict) -> None:
    ok = actual == expected
    checks[label] = {"actual": actual, "expected": expected, "match": ok}
    say(f"  {'OK     ' if ok else 'DIFFERS'} {label}: {actual:,} (notebook: {expected:,})")


def effect_report(ds: Dataset, say: Callable[[str], None]) -> dict:
    """Observed balance movement per type; confirms the reference data in sql/02_seed_reference.sql."""
    say("Observed balance effect per transaction type (share of rows whose balance went down / unchanged / up):")
    report: dict[str, dict] = {}
    d_orig, d_dest = ds.new_o - ds.old_o, ds.new_d - ds.old_d
    for code, name in enumerate(ds.classes):
        m = ds.type_codes == code
        row = {}
        for side, delta in (("origin", d_orig[m]), ("dest", d_dest[m])):
            dn, up = float((delta < 0).mean()), float((delta > 0).mean())
            row[side] = {"down": dn, "same": 1.0 - dn - up, "up": up,
                         "dominant": (-1 if dn > up else +1) if (dn or up) else 0}
        report[name] = row
        exp = EXPECTED_EFFECTS.get(name)
        verdict = ""
        if exp:
            ok = (row["origin"]["dominant"], row["dest"]["dominant"]) == exp
            verdict = "  -> matches seed" if ok else f"  -> CHECK: seed assumes origin {exp[0]:+d}, dest {exp[1]:+d}"
        say(f"  {name:<9} origin {row['origin']['down']:6.1%}/{row['origin']['same']:6.1%}/{row['origin']['up']:6.1%}"
            f"   dest {row['dest']['down']:6.1%}/{row['dest']['same']:6.1%}/{row['dest']['up']:6.1%}{verdict}")
    return report


def compute(csv_path: Path, *, expected: dict | None = NOTEBOOK_EXPECTED,
            say: Callable[[str], None] = _say) -> tuple[dict, Context]:
    """Replay the notebook's preprocessing and return (preprocessing config, context)."""
    ds = load_dataset(csv_path, say)
    checks: dict = {}

    # ---- type encoding (cell 19) -------------------------------------------------
    encoding = {name: i for i, name in enumerate(ds.classes)}
    say(f"Transaction types (LabelEncoder order): {encoding}")
    if encoding != DEFAULT_TYPE_ENCODING:
        raise ExportError(
            f"The dataset's transaction types encode as {encoding}, but the project (sql/02_seed_reference.sql, "
            f"app/ml/features.py) assumes {DEFAULT_TYPE_ENCODING}. The saved model was trained on the notebook's "
            "encoding, so update the seed data to match before continuing."
        )

    # ---- dataset sanity vs notebook (cells 3, 9) ------------------------------------
    say("Dataset cross-check against the notebook's printed output:")
    if expected:
        _check("rows", ds.n, expected["rows"], say, checks)
        _check("fraud rows", int(ds.y.sum()), expected["fraud_rows"], say, checks)

    # ---- p99 (cell 9) ----------------------------------------------------------------
    p99 = float(pd.Series(ds.amount).quantile(P99_QUANTILE))
    above = int((ds.amount > p99).sum())
    say(f"p99_amount = {p99!r}")
    if expected:
        _check("rows above p99", above, expected["above_p99"], say, checks)

    # ---- effects (informational) ---------------------------------------------------------
    effects = effect_report(ds, say)

    # ---- features (cells 9, 14, 18, 19) ------------------------------------------------
    say("Engineering the 9 features ...")
    diff_orig = ds.old_o - ds.new_o
    diff_dest = ds.new_d - ds.old_d
    raw = engineer_features(step=ds.step, amount=ds.amount, balance_diff_orig=diff_orig,
                            balance_diff_dest=diff_dest, type_enc=ds.type_codes,
                            p99_amount=p99, night_hours=NOTEBOOK_NIGHT_HOURS)
    y = ds.y
    n = ds.n
    del ds, diff_orig, diff_dest

    # ---- the notebook's split (cell 21) ---------------------------------------------------
    say(f"Reproducing train_test_split(test_size={TEST_SIZE}, stratify=y, random_state={RANDOM_STATE}) ...")
    train_idx, test_idx = train_test_split(np.arange(n), test_size=TEST_SIZE, stratify=y, random_state=RANDOM_STATE)
    if expected:
        _check("test rows", len(test_idx), expected["test_rows"], say, checks)
        _check("test fraud rows", int(y[test_idx].sum()), expected["test_fraud_rows"], say, checks)

    # ---- RobustScaler fitted on TRAIN only (cell 21), column by column to save memory --------------
    say("Fitting RobustScaler on the training split ...")
    centers, scales = [], []
    for name in FEATURES:
        scaler = RobustScaler().fit(raw[name][train_idx].reshape(-1, 1))
        centers.append(float(scaler.center_[0]))
        scales.append(float(scaler.scale_[0]))
        say(f"  {name:<18} center={centers[-1]!r:<24} scale={scales[-1]!r}")

    config = {
        "_meta": {
            "status": STATUS_VERIFIED,
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source_csv": str(csv_path),
            "rows": n,
            "fraud_rows": int(y.sum()),
            "split": {"test_size": TEST_SIZE, "random_state": RANDOM_STATE, "stratified": True},
            "p99_quantile": P99_QUANTILE,
            "versions": {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__,
                         "scikit-learn": __import__("sklearn").__version__},
            "notebook_crosscheck": checks,
            "observed_effects": effects,
        },
        "features": list(FEATURES),
        "p99_amount": p99,
        "night_hours": list(NOTEBOOK_NIGHT_HOURS),
        "type_encoding": encoding,
        "scaler_center": centers,
        "scaler_scale": scales,
    }
    FeatureBuilder(config)            # raises PreprocessingNotReady if anything is inconsistent
    return config, Context(raw=raw, train_idx=train_idx, test_idx=test_idx, y=y, checks=checks)


# ------------------------------------------------------------------------ model check
def find_model(explicit: Path | None) -> Path | None:
    if explicit:
        return explicit
    return next((p for p in MODEL_CANDIDATES if p.exists()), None)


def verify_model(model_path: Path, config: dict, ctx: Context, say: Callable[[str], None],
                 expected: dict | None = NOTEBOOK_EXPECTED) -> dict:
    """Load the saved artifact and test it on the rebuilt, scaled test split."""
    import joblib
    from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score

    say(f"Loading model artifact {model_path} ...")
    try:
        artifact = joblib.load(model_path)
    except ModuleNotFoundError as exc:
        raise ExportError(f"Cannot unpickle the model: package '{exc.name}' is not installed. Run: pip install -r requirements.txt") from exc
    missing = {"model", "threshold", "features"} - set(artifact)
    if missing:
        raise ExportError(f"Model artifact is missing keys {sorted(missing)}")

    feats, threshold = list(artifact["features"]), float(artifact["threshold"])
    result: dict = {"model_file": str(model_path), "model_name": artifact.get("model_name"),
                    "artifact_threshold": threshold, "feature_order_matches": feats == FEATURES}
    say(f"  model_name={artifact.get('model_name')}  threshold={threshold!r}")
    say(f"  feature order {'matches' if feats == FEATURES else 'DIFFERS from'} the expected order")
    if feats != FEATURES:
        raise ExportError(f"The model's feature list {feats} differs from the project's {FEATURES}. Not continuing.")
    diff = abs(threshold - CONFIGURED_THRESHOLD)
    result["threshold_matches_configured"] = diff < 1e-9
    say(f"  threshold vs configured {CONFIGURED_THRESHOLD}: {'identical' if diff < 1e-9 else f'DIFFERENT (|diff|={diff:.3g})'}")

    # scaled TEST split, exactly as the notebook produced X_test
    center, scale = np.asarray(config["scaler_center"]), np.asarray(config["scaler_scale"])
    X = pd.DataFrame(
        np.column_stack([ctx.raw[name][ctx.test_idx] for name in FEATURES]) - center, columns=FEATURES) / scale
    y_test = ctx.y[ctx.test_idx]

    say(f"Scoring {len(X):,} test rows ...")
    model = artifact["model"]
    scores = np.concatenate([model.predict_proba(X.iloc[i:i + 200_000][feats])[:, 1] for i in range(0, len(X), 200_000)])

    pred = scores >= threshold
    tp = int((pred & (y_test == 1)).sum()); fn = int((~pred & (y_test == 1)).sum())
    fp = int((pred & (y_test == 0)).sum()); tn = int((~pred & (y_test == 0)).sum())
    roc, pr = float(roc_auc_score(y_test, scores)), float(average_precision_score(y_test, scores))
    result.update(confusion={"tp": tp, "fn": fn, "fp": fp, "tn": tn}, roc_auc=roc, pr_auc=pr,
                  recall=tp / (tp + fn), precision=tp / (tp + fp) if tp + fp else None)
    prec_txt = f"{result['precision']:.3f}" if result["precision"] is not None else "n/a (no positive predictions)"
    say(f"  at threshold {threshold:.6f}: TP={tp:,} FN={fn:,} FP={fp:,} TN={tn:,}  "
        f"recall={result['recall']:.3f} precision={prec_txt}")
    say(f"  ROC-AUC={roc:.5f} (notebook cell 33: 0.99821)  PR-AUC={pr:.5f} (notebook cell 33: 0.86172)")

    if expected:
        exp = expected["confusion"]
        exact = {"tp": tp, "fn": fn, "fp": fp, "tn": tn} == exp
        close = abs(tp - exp["tp"]) <= 15 and abs(fp - exp["fp"]) <= 150
        result["matches_notebook_exactly"] = exact
        result["matches_notebook_closely"] = close
        if exact:
            say("  RESULT: identical to notebook cell 38 -> the rebuilt preprocessing reproduces training exactly.")
        elif close:
            say("  RESULT: very close to cell 38 (small drift is normal if xgboost/scikit-learn versions differ).")
        else:
            say("  RESULT: DIFFERS from notebook cell 38. Either this is not the same dataset/model, or the notebook "
                "was re-run with different settings. Do not trust predictions until this is explained.")

    # Discrepancy documented in docs/REPORT.md: the notebook chose the threshold (cell 27) with the
    # UNTUNED XGBoost but saved the TUNED one (cells 30, 36). Show what cell 27's rule gives for this model.
    precision, recall, thresholds = precision_recall_curve(y_test, scores)
    ok = recall[:-1] >= 0.90
    if ok.any():
        best = int(np.argmax(np.where(ok, precision[:-1], -1)))
        result["cell27_rule_for_saved_model"] = {"threshold": float(thresholds[best]),
                                                  "precision": float(precision[best]), "recall": float(recall[best])}
        say(f"  For reference, notebook cell 27's rule (recall>=0.90, best precision) applied to THIS model gives "
            f"threshold {thresholds[best]:.6f} (precision {precision[best]:.3f}, recall {recall[best]:.3f}). "
            "The app keeps the artifact's threshold; change it only by deliberate decision.")
    return result


# ----------------------------------------------------------------------------- output
def write_config(config: dict, out_path: Path, say: Callable[[str], None]) -> Path | None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    if out_path.exists():
        backup = out_path.with_name(f"{out_path.name}.bak-{time.strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(out_path, backup)
        say(f"Backed up the previous file to {backup.name}")
    tmp = out_path.with_name(out_path.name + ".tmp")
    tmp.write_text(json.dumps(config, indent=2) + "\n")
    os.replace(tmp, out_path)               # atomic: never leaves a half-written file
    say(f"Wrote {out_path}")
    return backup


def run(csv_path: Path, out_path: Path, *, model_path: Path | None = None, check_model: bool = True,
        expected: dict | None = NOTEBOOK_EXPECTED, say: Callable[[str], None] = _say) -> dict:
    started = time.time()
    config, ctx = compute(csv_path, expected=expected, say=say)

    model_file = find_model(model_path) if check_model else None
    if model_path and not model_path.exists():
        raise ExportError(f"--model file not found: {model_path}")
    if model_file:
        try:
            config["_meta"]["model_check"] = verify_model(model_file, config, ctx, say, expected)
        except ExportError:
            raise
        except Exception as exc:       # keep the essential output even if the optional check fails
            say(f"WARNING: model check could not complete ({type(exc).__name__}: {exc}). preprocessing.json is still written.")
    elif check_model:
        say("No model file found (looked in models/ and the project root) - skipping the optional model check. "
            "Re-run after copying best_fraud_model_tuned.pkl into models/ to verify it.")

    write_config(config, out_path, say)
    mem = _peak_memory_mb()
    say(f"Done in {time.time() - started:,.0f}s" + (f" (peak memory about {mem:,.0f} MB)." if mem else "."))
    return config


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Recompute models/preprocessing.json from the full Fraud.csv.")
    ap.add_argument("--csv", type=Path, default=None, help=f"path to Fraud.csv (default: {DEFAULT_CSV})")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="where to write the JSON (default: models/preprocessing.json)")
    ap.add_argument("--model", type=Path, default=None, help="path to best_fraud_model_tuned.pkl (default: auto-detect)")
    ap.add_argument("--skip-model-check", action="store_true", help="do not load the model / verify results")
    args = ap.parse_args(argv)

    csv_path = args.csv or (DEFAULT_CSV if DEFAULT_CSV.exists() else FALLBACK_CSV if FALLBACK_CSV.exists() else DEFAULT_CSV)
    try:
        run(csv_path.expanduser(), args.out, model_path=args.model, check_model=not args.skip_model_check)
    except ExportError as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 2
    except MemoryError:
        print("\nERROR: ran out of memory. Close other applications and try again.", file=sys.stderr)
        return 2
    except Exception:
        print("\nUNEXPECTED ERROR (please send this to whoever is helping you):", file=sys.stderr)
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
