import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agriml.data import clean_price_frame  # noqa: E402
from agriml.features import (  # noqa: E402
    MIN_HISTORY_WEEKS,
    InsufficientHistoryError,
    build_latest_features,
    build_training_rows,
    to_weekly,
)
from agriml.modeling import chronological_split  # noqa: E402
from agriml.predictor import ModelUnavailableError, PricePredictor  # noqa: E402


def make_series(n_days=400, start="2025-01-01", base=2000.0, seed=0):
    rng = np.random.default_rng(seed)
    d = pd.date_range(start, periods=n_days, freq="D")
    p = base * np.exp(np.cumsum(rng.normal(0, 0.01, n_days)))
    return pd.DataFrame({"state": "S", "district": "D", "market": "M", "commodity": "C", "arrival_date": d,
                         "min_price": p * 0.95, "max_price": p * 1.05, "modal_price": p})


def test_cleaning_drops_invalid_rows_without_inventing_values():
    raw = pd.DataFrame({
        "state": ["S"] * 6, "district": ["D"] * 6, "market": ["M"] * 6, "commodity": ["C"] * 6,
        "arrival_date": ["2026-01-01", "02/01/2026", "garbage", "2026-01-04", "2026-01-05", "2026-01-01"],
        "min_price": ["90", "90", "90", "-5", "120", "91"],
        "max_price": ["110", "110", "110", "110", "110", "111"],
        "modal_price": ["100", "100", "100", "100", "100", "101"],
    })
    df, report = clean_price_frame(raw)
    assert len(df) == 2  # 2026-01-01 (last duplicate kept) and 2026-01-02
    assert report.dropped == {"invalid date": 1, "price out of range": 1, "min/modal/max out of order": 1,
                              "duplicate observation": 1}
    assert df.loc[df.arrival_date == "2026-01-01", "modal_price"].item() == 101


def test_cleaning_requires_columns():
    with pytest.raises(ValueError, match="missing required columns"):
        clean_price_frame(pd.DataFrame({"state": ["S"]}))


def test_features_do_not_use_future_prices():
    df = make_series()
    rows = build_training_rows(to_weekly(df))
    feature_cols = [c for c in rows.columns if c.startswith(("lag_", "roll_", "volatility", "momentum", "log_price"))]
    # Perturb every price after a cut-off: features at/before the cut-off must be unchanged.
    cut = pd.Timestamp("2025-08-31")
    df2 = df.copy()
    df2.loc[df2.arrival_date > cut, ["min_price", "max_price", "modal_price"]] *= 3
    rows2 = build_training_rows(to_weekly(df2))
    a = rows[rows.anchor_week <= cut].set_index(["anchor_week", "horizon"])[feature_cols]
    b = rows2[rows2.anchor_week <= cut].set_index(["anchor_week", "horizon"])[feature_cols]
    pd.testing.assert_frame_equal(a, b)


def test_targets_are_exact_horizon_and_observed():
    rows = build_training_rows(to_weekly(make_series()))
    assert ((rows.target_week - rows.anchor_week).dt.days == rows.horizon * 7).all()
    assert np.allclose(rows.target, np.log(rows.target_price / rows.base_price))
    assert (rows.history_len >= MIN_HISTORY_WEEKS).all()


def test_chronological_split_has_no_overlap_or_lookahead():
    rows = build_training_rows(to_weekly(make_series(n_days=700)))
    train, val, test, cut = chronological_split(rows, 8, 8)
    assert train.anchor_week.max() < val.anchor_week.min() <= val.anchor_week.max() < test.anchor_week.min()
    assert train.target_week.max() < cut["val_start"] and val.target_week.max() < cut["test_start"]


def test_latest_features_require_history():
    short = make_series(n_days=40)
    with pytest.raises(InsufficientHistoryError):
        build_latest_features(short[["arrival_date", "modal_price"]], "C", "S", "D", "M", 1)
    with pytest.raises(InsufficientHistoryError):
        build_latest_features(short.iloc[0:0][["arrival_date", "modal_price"]], "C", "S", "D", "M", 1)
    with pytest.raises(ValueError):
        build_latest_features(make_series()[["arrival_date", "modal_price"]], "C", "S", "D", "M", 3)


def test_long_gap_breaks_series():
    df = make_series(n_days=300)
    gap = (df.arrival_date > "2025-09-01") & (df.arrival_date < "2025-10-15")
    df = df[~gap]
    with pytest.raises(InsufficientHistoryError):  # only ~2 weeks of data after the gap
        build_latest_features(df[["arrival_date", "modal_price"]], "C", "S", "D", "M", 1)


def test_train_save_load_predict_roundtrip(tmp_path):
    import train as train_module

    frames = [make_series(n_days=700, start="2024-06-01", base=b, seed=s).assign(commodity=c)
              for c, b, s in [("A", 2000, 1), ("B", 5000, 2)]]
    csv = tmp_path / "t.csv"
    pd.concat(frames).assign(arrival_date=lambda d: d.arrival_date.dt.strftime("%Y-%m-%d")).to_csv(csv, index=False)
    out = tmp_path / "m.joblib"
    meta = train_module.train(csv, out, quiet=True, val_weeks=8, test_weeks=8)
    assert meta["data_kind"] == "synthetic_demo" and meta["model_version"].endswith("-demo")
    assert {"naive_last_value", "ridge", "random_forest", "hist_gradient_boosting"} <= set(meta["validation"])
    assert meta["test"]["selected"]["mae"] > 0 and (out.with_suffix(".metrics.json")).exists()

    pred = PricePredictor.load(out)
    hist = frames[0][["arrival_date", "modal_price"]]
    r = pred.predict(hist, "A", "S", "D", "M", 2)
    assert r["predicted_price"] > 0 and r["is_demo_model"] and r["horizon_weeks"] == 2
    assert not pred.supports("Z", "S", "D", "M")


def test_missing_and_corrupt_model(tmp_path):
    with pytest.raises(ModelUnavailableError):
        PricePredictor.load(tmp_path / "missing.joblib")
    bad = tmp_path / "bad.joblib"
    bad.write_text("x")
    with pytest.raises(ModelUnavailableError):
        PricePredictor.load(bad)
