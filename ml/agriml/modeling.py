"""Model candidates, chronological splitting, evaluation and selection."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .features import CATEGORICAL_FEATURES, FEATURE_COLUMNS, NUMERIC_FEATURES


class NaiveLastValue:
    """Baseline: next price equals the current price (predicted log-change of 0)."""

    name = "naive_last_value"

    def fit(self, X, y):
        return self

    def predict(self, X):
        return np.zeros(len(X))


class MovingAverageReversion:
    """Baseline: next price equals the 4-week moving average."""

    name = "moving_average_4w"

    def fit(self, X, y):
        return self

    def predict(self, X):
        return np.log(X["roll_mean_ratio_4"].to_numpy(dtype=float))


def _preprocessor(scale: bool) -> ColumnTransformer:
    num = StandardScaler() if scale else "passthrough"
    return ColumnTransformer(
        [
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
            ("num", num, NUMERIC_FEATURES),
        ]
    )


def candidate_models(random_state: int = 42) -> dict:
    return {
        "naive_last_value": NaiveLastValue(),
        "moving_average_4w": MovingAverageReversion(),
        "ridge": Pipeline([("prep", _preprocessor(scale=True)), ("model", Ridge(alpha=1.0))]),
        "random_forest": Pipeline(
            [
                ("prep", _preprocessor(scale=False)),
                ("model", RandomForestRegressor(n_estimators=200, min_samples_leaf=10, max_features=0.5,
                                                n_jobs=-1, random_state=random_state)),
            ]
        ),
        "hist_gradient_boosting": Pipeline(
            [
                ("prep", _preprocessor(scale=False)),
                ("model", HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_leaf_nodes=15,
                                                        min_samples_leaf=40, l2_regularization=1.0,
                                                        random_state=random_state)),
            ]
        ),
    }


BASELINES = {"naive_last_value", "moving_average_4w"}


def chronological_split(rows: pd.DataFrame, val_weeks: int = 16, test_weeks: int = 16):
    """Split by anchor week: train | validation | test, oldest to newest.

    Rows whose *target* week falls inside a later period are purged from the earlier
    period, so no training target overlaps the evaluation window (no look-ahead).
    """
    last_week = rows["anchor_week"].max()
    test_start = last_week - pd.Timedelta(weeks=test_weeks - 1)
    val_start = test_start - pd.Timedelta(weeks=val_weeks)
    train = rows[(rows["anchor_week"] < val_start) & (rows["target_week"] < val_start)]
    val = rows[(rows["anchor_week"] >= val_start) & (rows["anchor_week"] < test_start)
               & (rows["target_week"] < test_start)]
    test = rows[rows["anchor_week"] >= test_start]
    return train, val, test, {"val_start": val_start, "test_start": test_start}


def price_metrics(frame: pd.DataFrame, pred_log_ratio: np.ndarray) -> dict:
    """MAE / RMSE / MAPE in price units (Rs per unit), overall and per horizon."""
    pred_price = frame["base_price"].to_numpy() * np.exp(pred_log_ratio)
    actual = frame["target_price"].to_numpy()
    err = pred_price - actual
    out = {
        "mae": float(np.mean(np.abs(err))),
        "rmse": float(np.sqrt(np.mean(err ** 2))),
        "mape_pct": float(np.mean(np.abs(err) / actual) * 100),
        "n": int(len(frame)),
        "by_horizon": {},
    }
    for h, idx in frame.groupby("horizon").groups.items():
        mask = frame.index.isin(idx)
        e = err[mask]
        out["by_horizon"][str(int(h))] = {
            "mae": float(np.mean(np.abs(e))),
            "rmse": float(np.sqrt(np.mean(e ** 2))),
            "mape_pct": float(np.mean(np.abs(e) / actual[mask]) * 100),
            "n": int(mask.sum()),
        }
    return out


def residual_bands(frame: pd.DataFrame, pred_log_ratio: np.ndarray) -> dict:
    """Empirical 10th/90th percentile of log-ratio errors per horizon (for a typical range)."""
    resid = frame["target"].to_numpy() - pred_log_ratio
    bands = {}
    for h, idx in frame.groupby("horizon").groups.items():
        r = resid[frame.index.isin(idx)]
        bands[str(int(h))] = {"p10": float(np.quantile(r, 0.10)), "p90": float(np.quantile(r, 0.90))}
    return bands


def fit_predict(model, train: pd.DataFrame, evaluate: pd.DataFrame) -> np.ndarray:
    model.fit(train[FEATURE_COLUMNS], train["target"])
    return model.predict(evaluate[FEATURE_COLUMNS])
