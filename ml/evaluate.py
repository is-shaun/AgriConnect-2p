"""Evaluate a saved model on a CSV, optionally only on weeks after a cut-off date.

    python ml/evaluate.py                                  # prints the stored training metrics
    python ml/evaluate.py --csv new_prices.csv --after 2026-07-01

When ``--csv`` is given, rows are rebuilt with the same feature code used in training and
scored against the naive last-value baseline. Only rows whose anchor week is after
``--after`` are scored, so you can evaluate on data the model has never seen.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from agriml.data import load_price_csv  # noqa: E402
from agriml.features import FEATURE_COLUMNS, build_training_rows, to_weekly  # noqa: E402
from agriml.modeling import price_metrics  # noqa: E402
from agriml.predictor import PricePredictor  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=str(HERE / "artifacts" / "price_model.joblib"))
    ap.add_argument("--csv")
    ap.add_argument("--after", help="only score anchor weeks after this date (YYYY-MM-DD)")
    a = ap.parse_args()

    predictor = PricePredictor.load(a.model)
    meta = predictor.metadata
    print(f"Model {meta['model_version']} ({meta['model_name']}), data kind: {meta['data_kind']}")
    if not a.csv:
        print(json.dumps({"validation": meta["validation"], "test": meta["test"]}, indent=2))
        return
    df, report = load_price_csv(a.csv)
    rows = build_training_rows(to_weekly(df), predictor.horizons)
    if a.after:
        rows = rows[rows["anchor_week"] > pd.Timestamp(a.after)]
    if rows.empty:
        raise SystemExit("No evaluable rows (need enough history plus observed future weeks).")
    pred = predictor.pipeline.predict(rows[FEATURE_COLUMNS])
    out = {"model": price_metrics(rows.reset_index(drop=True), pred),
           "naive_last_value": price_metrics(rows.reset_index(drop=True), np.zeros(len(rows)))}
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
