"""Load a saved model artifact and produce predictions for one crop/market series."""

from __future__ import annotations

import math
from pathlib import Path

import joblib
import pandas as pd

from .data import series_key
from .features import FEATURE_VERSION, HORIZONS, build_latest_features

ARTIFACT_FORMAT = "agriconnect-price-model/1"


class ModelUnavailableError(RuntimeError):
    """No usable model artifact is available."""


class UnsupportedSeriesError(ValueError):
    """The crop/market combination was not part of the model's training data."""


class PricePredictor:
    def __init__(self, artifact: dict):
        if artifact.get("format") != ARTIFACT_FORMAT:
            raise ModelUnavailableError("Model artifact has an unknown format.")
        meta = artifact["metadata"]
        if meta.get("feature_version") != FEATURE_VERSION:
            raise ModelUnavailableError(
                f"Model was trained with feature version {meta.get('feature_version')}, "
                f"but this code uses version {FEATURE_VERSION}. Retrain the model."
            )
        self.pipeline = artifact["pipeline"]
        self.metadata = meta
        self._series = set(meta.get("series", []))

    @classmethod
    def load(cls, path) -> "PricePredictor":
        path = Path(path)
        if not path.exists():
            raise ModelUnavailableError(f"No trained model found at {path}. Run `python ml/train.py` first.")
        try:
            artifact = joblib.load(path)
        except Exception as exc:  # corrupted file, incompatible pickle, …
            raise ModelUnavailableError(f"Could not load model artifact: {exc}") from exc
        return cls(artifact)

    @property
    def version(self) -> str:
        return self.metadata["model_version"]

    @property
    def is_demo(self) -> bool:
        return self.metadata.get("data_kind") != "real"

    @property
    def horizons(self) -> list[int]:
        return list(self.metadata.get("horizons", HORIZONS))

    def supports(self, commodity, state, district, market) -> bool:
        return series_key(state, district, market, commodity) in self._series

    def predict(self, history: pd.DataFrame, commodity: str, state: str, district: str,
                market: str, horizon: int) -> dict:
        if horizon not in self.horizons:
            raise ValueError(f"Unsupported horizon {horizon}; supported: {self.horizons}")
        if not self.supports(commodity, state, district, market):
            raise UnsupportedSeriesError(
                f"The current model was not trained on {commodity} at {market} ({district}, {state})."
            )
        row, ctx = build_latest_features(history, commodity, state, district, market, horizon)
        log_ratio = float(self.pipeline.predict(row)[0])
        predicted = ctx["base_price"] * math.exp(log_ratio)
        band = self.metadata.get("residual_bands", {}).get(str(horizon))
        low = high = None
        if band:
            low = ctx["base_price"] * math.exp(log_ratio + band["p10"])
            high = ctx["base_price"] * math.exp(log_ratio + band["p90"])
        target_week = ctx["base_week"] + pd.Timedelta(weeks=horizon)
        return {
            "predicted_price": round(predicted, 2),
            "typical_range": {"low": round(low, 2), "high": round(high, 2)} if band else None,
            "base_price": round(ctx["base_price"], 2),
            "base_week_ending": ctx["base_week"].date().isoformat(),
            "target_week_ending": target_week.date().isoformat(),
            "last_observation_date": ctx["last_observation_date"].date().isoformat(),
            "weeks_of_history": ctx["weeks_of_history"],
            "horizon_weeks": horizon,
            "model_version": self.version,
            "model_name": self.metadata.get("model_name"),
            "is_demo_model": self.is_demo,
        }
