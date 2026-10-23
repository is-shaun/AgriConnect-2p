"""Loading and validating historical crop-price data.

Documented CSV format (one row per crop / market / observation date):

    state,district,market,commodity,category,unit,arrival_date,min_price,max_price,modal_price,source

* ``arrival_date`` – ISO date (YYYY-MM-DD). DD/MM/YYYY is also accepted (Agmarknet style).
* prices – positive numbers, in ``unit`` (normally Rs/quintal), with
  ``min_price <= modal_price <= max_price``.
* ``source`` – free text naming where the record came from.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = [
    "state",
    "district",
    "market",
    "commodity",
    "arrival_date",
    "min_price",
    "max_price",
    "modal_price",
]
OPTIONAL_COLUMNS = {"category": "Uncategorised", "unit": "Rs/quintal", "source": "unknown"}
PRICE_COLUMNS = ["min_price", "max_price", "modal_price"]
MAX_REASONABLE_PRICE = 1_000_000  # Rs/quintal; anything above is treated as a data-entry error


@dataclass
class CleaningReport:
    input_rows: int = 0
    output_rows: int = 0
    dropped: dict = field(default_factory=dict)

    def drop(self, reason: str, count: int) -> None:
        if count:
            self.dropped[reason] = self.dropped.get(reason, 0) + int(count)


def _parse_dates(series: pd.Series) -> pd.Series:
    iso = pd.to_datetime(series, format="%Y-%m-%d", errors="coerce")
    missing = iso.isna()
    if missing.any():
        dmy = pd.to_datetime(series[missing], format="%d/%m/%Y", errors="coerce")
        iso.loc[missing] = dmy
    return iso


def clean_price_frame(df: pd.DataFrame) -> tuple[pd.DataFrame, CleaningReport]:
    """Validate and clean a raw price frame. Returns (clean_df, report).

    Invalid rows are dropped (never "repaired" with invented values):
    unparseable dates, non-numeric / non-positive / absurd prices, and
    min/modal/max ordering violations. Exact duplicate keys keep the last row.
    """
    report = CleaningReport(input_rows=len(df))
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"CSV is missing required columns: {', '.join(missing)}")
    for col, default in OPTIONAL_COLUMNS.items():
        if col not in df.columns:
            df[col] = default
        df[col] = df[col].fillna(default)

    for col in ["state", "district", "market", "commodity", "category", "unit", "source"]:
        df[col] = df[col].astype(str).str.strip()
    blank = df[["state", "district", "market", "commodity"]].eq("").any(axis=1)
    report.drop("blank identifier", blank.sum())
    df = df[~blank]

    df["arrival_date"] = _parse_dates(df["arrival_date"].astype(str).str.strip())
    bad_date = df["arrival_date"].isna()
    report.drop("invalid date", bad_date.sum())
    df = df[~bad_date]

    for col in PRICE_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    bad_num = df[PRICE_COLUMNS].isna().any(axis=1)
    report.drop("missing or non-numeric price", bad_num.sum())
    df = df[~bad_num]

    bad_range = (df[PRICE_COLUMNS] <= 0).any(axis=1) | (df[PRICE_COLUMNS] > MAX_REASONABLE_PRICE).any(axis=1)
    report.drop("price out of range", bad_range.sum())
    df = df[~bad_range]

    bad_order = (df["min_price"] > df["modal_price"]) | (df["modal_price"] > df["max_price"])
    report.drop("min/modal/max out of order", bad_order.sum())
    df = df[~bad_order]

    key = ["state", "district", "market", "commodity", "arrival_date"]
    dup = df.duplicated(subset=key, keep="last")
    report.drop("duplicate observation", dup.sum())
    df = df[~dup]

    df = df.sort_values(key).reset_index(drop=True)
    report.output_rows = len(df)
    return df, report


def load_price_csv(path) -> tuple[pd.DataFrame, CleaningReport]:
    raw = pd.read_csv(path, dtype=str, keep_default_na=True)
    return clean_price_frame(raw)


def series_key(state: str, district: str, market: str, commodity: str) -> str:
    """Stable identifier for one crop/market price series."""
    return "|".join(s.strip().lower() for s in (commodity, state, district, market))


def summarize(df: pd.DataFrame) -> dict:
    return {
        "rows": int(len(df)),
        "series": int(df.groupby(["commodity", "state", "district", "market"]).ngroups) if len(df) else 0,
        "date_min": df["arrival_date"].min().date().isoformat() if len(df) else None,
        "date_max": df["arrival_date"].max().date().isoformat() if len(df) else None,
        "median_modal_price": float(np.median(df["modal_price"])) if len(df) else None,
    }
