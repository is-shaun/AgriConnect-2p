"""Train the AgriConnect crop-price model.

    python ml/train.py                                   # demo data -> ml/artifacts/price_model.joblib
    python ml/train.py --csv my_agmarknet_export.csv --data-kind real

Steps: load + validate CSV -> weekly series -> leakage-safe features -> chronological
train/validation/test split -> compare baselines and regressors on validation MAE ->
refit the winner on train+validation, report held-out test metrics -> refit on all data
and save the complete preprocessing+model pipeline with metadata via joblib.

``--data-kind`` must be ``real`` only when the CSV contains genuine, properly licensed
market observations. Anything else is recorded as a demo model and the API labels every
prediction from it as a demo estimate.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
import sklearn

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from agriml.data import load_price_csv, series_key, summarize  # noqa: E402
from agriml.features import FEATURE_COLUMNS, FEATURE_VERSION, HORIZONS, MIN_HISTORY_WEEKS, build_training_rows, to_weekly  # noqa: E402
from agriml.modeling import (  # noqa: E402
    BASELINES,
    candidate_models,
    chronological_split,
    fit_predict,
    price_metrics,
    residual_bands,
)
from agriml.predictor import ARTIFACT_FORMAT  # noqa: E402

DEFAULT_CSV = HERE / "data" / "demo_market_prices.csv"
DEFAULT_OUT = HERE / "artifacts" / "price_model.joblib"


def train(csv_path, out_path, data_kind="synthetic_demo", val_weeks=16, test_weeks=16, quiet=False):
    log = (lambda *a: None) if quiet else print
    df, report = load_price_csv(csv_path)
    log(f"Loaded {report.input_rows:,} rows; kept {report.output_rows:,}; dropped {report.dropped or 'none'}")
    if df.empty:
        raise SystemExit("No valid rows to train on.")
    weekly = to_weekly(df)
    rows = build_training_rows(weekly, HORIZONS)
    if rows["anchor_week"].nunique() < MIN_HISTORY_WEEKS + val_weeks + test_weeks:
        raise SystemExit("Not enough weeks of history for a train/validation/test split.")
    train_df, val_df, test_df, cut = chronological_split(rows, val_weeks, test_weeks)
    log(f"Training rows: train={len(train_df):,} val={len(val_df):,} test={len(test_df):,} "
        f"(validation from {cut['val_start'].date()}, test from {cut['test_start'].date()})")

    results = {}
    for name, model in candidate_models().items():
        pred = fit_predict(model, train_df, val_df)
        results[name] = price_metrics(val_df, pred)
        log(f"  {name:<24} val MAE={results[name]['mae']:8.1f}  RMSE={results[name]['rmse']:8.1f}  "
            f"MAPE={results[name]['mape_pct']:5.2f}%")

    best = min(results, key=lambda n: results[n]["mae"])
    best_baseline = min(BASELINES, key=lambda n: results[n]["mae"])
    log(f"Selected '{best}' by validation MAE (best baseline: '{best_baseline}').")

    # Honest held-out estimate: refit selected model and the best baseline on train+val, score on test.
    trainval = pd.concat([train_df, val_df])
    model_test = candidate_models()[best]
    test_pred = fit_predict(model_test, trainval, test_df)
    test_metrics = price_metrics(test_df, test_pred)
    base_metrics = price_metrics(test_df, fit_predict(candidate_models()[best_baseline], trainval, test_df))
    skill = 1 - test_metrics["mae"] / base_metrics["mae"] if base_metrics["mae"] else 0.0
    bands = residual_bands(test_df, test_pred)
    log(f"Test MAE={test_metrics['mae']:.1f} (baseline {base_metrics['mae']:.1f}; skill {skill:+.1%})")

    # Deployment model: refit on every available row.
    final = candidate_models()[best]
    final.fit(rows[FEATURE_COLUMNS], rows["target"])

    series = sorted({series_key(s, d, m, c) for c, s, d, m in
                     weekly[["commodity", "state", "district", "market"]].drop_duplicates().itertuples(index=False)})
    trained_at = datetime.now(timezone.utc)
    version = f"{best}-{trained_at:%Y%m%d%H%M%S}" + ("-demo" if data_kind != "real" else "")
    metadata = {
        "model_version": version,
        "model_name": best,
        "data_kind": data_kind,
        "trained_at": trained_at.isoformat(),
        "feature_version": FEATURE_VERSION,
        "horizons": list(HORIZONS),
        "horizon_unit": "weeks",
        "min_history_weeks": MIN_HISTORY_WEEKS,
        "target": "log(price[t+h] / price[t]) on weekly mean modal price",
        "training_data": {**summarize(df), "csv": str(Path(csv_path).name), "cleaning_dropped": report.dropped},
        "split": {"val_start": str(cut["val_start"].date()), "test_start": str(cut["test_start"].date()),
                  "val_weeks": val_weeks, "test_weeks": test_weeks},
        "validation": results,
        "test": {"selected": test_metrics, "baseline_name": best_baseline, "baseline": base_metrics,
                 "mae_skill_vs_baseline": skill},
        "residual_bands": bands,
        "series": series,
        "sklearn_version": sklearn.__version__,
        "notes": ("Metrics are in Rs/quintal on held-out weeks. R² is not reported: pooled across crops whose "
                  "price levels differ ~5x it is dominated by between-crop variance and overstates skill."),
    }
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"format": ARTIFACT_FORMAT, "pipeline": final, "metadata": metadata}, out_path, compress=3)
    (out_path.with_suffix(".metrics.json")).write_text(json.dumps(
        {k: v for k, v in metadata.items() if k != "series"}, indent=2, default=str))
    log(f"Saved model {version} to {out_path}")
    return metadata


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", default=str(DEFAULT_CSV))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--data-kind", choices=["synthetic_demo", "real"], default="synthetic_demo")
    ap.add_argument("--val-weeks", type=int, default=16)
    ap.add_argument("--test-weeks", type=int, default=16)
    args = ap.parse_args()
    if args.data_kind == "real" and Path(args.csv).resolve() == DEFAULT_CSV.resolve():
        raise SystemExit("The bundled CSV is synthetic demo data; it cannot be trained as --data-kind real.")
    train(args.csv, args.out, args.data_kind, args.val_weeks, args.test_weeks)


if __name__ == "__main__":
    main()
