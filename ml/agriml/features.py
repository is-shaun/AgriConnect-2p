"""Leakage-safe time-series feature engineering.

Every crop/market series is first regularised to a weekly grid (mean modal price per
week ending Sunday). Mandi data is irregular – markets close on holidays and some days
have no arrivals – so a weekly grid gives lags and rolling windows a consistent meaning.

For an anchor week *t* every feature uses only prices from weeks <= t. The training
target for horizon *h* is ``log(price[t+h] / price[t])``; the predicted price is
``price[t] * exp(prediction)``. Modelling the relative change lets one model serve
crops whose absolute price levels differ by an order of magnitude.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

FEATURE_VERSION = 1
HORIZONS = (1, 2, 4)  # weeks ahead supported by the model
LAGS = (1, 2, 4, 8)
WINDOWS = (4, 12)
MIN_HISTORY_WEEKS = 13  # longest lookback (12-week window + current week)
MAX_FILL_WEEKS = 2  # bridge at most 2 missing weeks; longer gaps break the series

SERIES_KEYS = ["commodity", "state", "district", "market"]
CATEGORICAL_FEATURES = ["commodity", "state", "market"]
NUMERIC_FEATURES = (
    [f"lag_ratio_{k}" for k in LAGS]
    + [f"roll_mean_ratio_{w}" for w in WINDOWS]
    + ["volatility_4", "momentum_4", "log_price", "week_sin", "week_cos", "horizon"]
)
FEATURE_COLUMNS = CATEGORICAL_FEATURES + NUMERIC_FEATURES


class InsufficientHistoryError(ValueError):
    """Raised when a series does not have enough recent history to build features."""


def to_weekly(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate cleaned daily observations to one modal price per series-week."""
    if df.empty:
        return pd.DataFrame(columns=SERIES_KEYS + ["week", "price", "observed"])
    out = []
    for keys, g in df.groupby(SERIES_KEYS, sort=True):
        s = g.set_index("arrival_date")["modal_price"].astype(float).resample("W-SUN").mean()
        observed = s.notna()
        s = s.ffill(limit=MAX_FILL_WEEKS)
        frame = pd.DataFrame({"week": s.index, "price": s.values, "observed": observed.values})
        for k, v in zip(SERIES_KEYS, keys):
            frame[k] = v
        out.append(frame.dropna(subset=["price"]))
    weekly = pd.concat(out, ignore_index=True)
    return weekly[SERIES_KEYS + ["week", "price", "observed"]]


def _series_features(g: pd.DataFrame) -> pd.DataFrame:
    """Compute backward-looking features for one regular weekly series."""
    g = g.sort_values("week").copy()
    # A gap longer than MAX_FILL_WEEKS splits the series into separate segments so
    # that lags never silently reach across missing months.
    gap = g["week"].diff().dt.days.fillna(7) > 7
    g["segment"] = gap.cumsum()
    parts = []
    for _, seg in g.groupby("segment"):
        p = seg["price"]
        f = seg.copy()
        for k in LAGS:
            f[f"lag_ratio_{k}"] = p.shift(k) / p
        for w in WINDOWS:
            f[f"roll_mean_ratio_{w}"] = p.rolling(w).mean() / p
        f["volatility_4"] = np.log(p).diff().rolling(4).std()
        f["momentum_4"] = np.log(p / p.shift(4))
        f["log_price"] = np.log(p)
        f["history_len"] = np.arange(1, len(seg) + 1)
        parts.append(f)
    out = pd.concat(parts)
    woy = out["week"].dt.isocalendar().week.astype(float)
    out["week_sin"] = np.sin(2 * np.pi * woy / 52.18)
    out["week_cos"] = np.cos(2 * np.pi * woy / 52.18)
    return out


def build_feature_frame(weekly: pd.DataFrame) -> pd.DataFrame:
    parts = [_series_features(g) for _, g in weekly.groupby(SERIES_KEYS, sort=True)]
    return pd.concat(parts, ignore_index=True) if parts else weekly.iloc[0:0]


def build_training_rows(weekly: pd.DataFrame, horizons=HORIZONS) -> pd.DataFrame:
    """Stack one row per (anchor week, horizon) with its future target.

    Columns: features + ``anchor_week``, ``target_week``, ``base_price``,
    ``target_price`` and ``target`` (log ratio).
    """
    feats = build_feature_frame(weekly)
    rows = []
    for _, g in feats.groupby(SERIES_KEYS + ["segment"], sort=False):
        g = g.sort_values("week")
        for h in horizons:
            r = g.copy()
            r["horizon"] = h
            r["target_price"] = g["price"].shift(-h)
            r["target_week"] = g["week"].shift(-h)
            r["target_observed"] = g["observed"].shift(-h)
            rows.append(r)
    data = pd.concat(rows, ignore_index=True)
    data = data[data["history_len"] >= MIN_HISTORY_WEEKS]
    # The target week must be exactly h weeks later and must be a real (not forward-filled)
    # observation, so the model is never trained to predict its own imputation.
    data = data.dropna(subset=NUMERIC_FEATURES + ["target_price"])
    expected = data["week"] + pd.to_timedelta(data["horizon"] * 7, unit="D")
    data = data[(data["target_week"] == expected) & (data["target_observed"] == True)]  # noqa: E712
    data = data.rename(columns={"week": "anchor_week", "price": "base_price"})
    data["target"] = np.log(data["target_price"] / data["base_price"])
    return data.reset_index(drop=True)


def build_latest_features(history: pd.DataFrame, commodity: str, state: str, district: str,
                          market: str, horizon: int) -> tuple[pd.DataFrame, dict]:
    """Build the single feature row for the most recent week of one series.

    ``history`` has columns ``arrival_date`` (datetime) and ``modal_price``.
    Returns (feature_row, context) where context holds base week and base price.
    """
    if horizon not in HORIZONS:
        raise ValueError(f"Unsupported horizon {horizon}; supported: {list(HORIZONS)}")
    if history is None or history.empty:
        raise InsufficientHistoryError("No price history is available for this crop and market.")
    h = history.copy()
    h["arrival_date"] = pd.to_datetime(h["arrival_date"])
    h["modal_price"] = pd.to_numeric(h["modal_price"], errors="coerce")
    h = h.dropna(subset=["arrival_date", "modal_price"])
    h = h[h["modal_price"] > 0]
    h["commodity"], h["state"], h["district"], h["market"] = commodity, state, district, market
    weekly = to_weekly(h)
    if weekly.empty:
        raise InsufficientHistoryError("No valid price history is available for this crop and market.")
    feats = build_feature_frame(weekly).sort_values("week")
    last = feats.iloc[[-1]].copy()
    if int(last["history_len"].iloc[0]) < MIN_HISTORY_WEEKS or last[NUMERIC_FEATURES[:-1]].isna().any(axis=1).iloc[0]:
        raise InsufficientHistoryError(
            f"At least {MIN_HISTORY_WEEKS} consecutive weeks of recent prices are required; "
            f"only {int(last['history_len'].iloc[0])} are available."
        )
    last["horizon"] = horizon
    context = {
        "base_week": last["week"].iloc[0],
        "base_price": float(last["price"].iloc[0]),
        "last_observation_date": h["arrival_date"].max(),
        "weeks_of_history": int(last["history_len"].iloc[0]),
    }
    return last[FEATURE_COLUMNS], context
