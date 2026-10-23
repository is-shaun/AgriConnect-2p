"""Bridges the Flask app and the shared ML package in ml/agriml."""

from __future__ import annotations

import logging
import sys
import threading
from datetime import date
from pathlib import Path

import pandas as pd
from flask import current_app
from sqlalchemy import select

from ..extensions import db
from ..models import MarketPrice

ML_DIR = Path(__file__).resolve().parents[3] / "ml"
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

from agriml.features import HORIZONS, InsufficientHistoryError  # noqa: E402,F401
from agriml.predictor import ModelUnavailableError, PricePredictor, UnsupportedSeriesError  # noqa: E402,F401

log = logging.getLogger(__name__)
_cache: dict = {}
_lock = threading.Lock()


def get_predictor() -> PricePredictor:
    """Load the model once per process; reload automatically if the artifact file changes."""
    path = Path(current_app.config["MODEL_PATH"])
    if not path.exists():
        raise ModelUnavailableError("No trained model is available. Run `python ml/train.py` and restart.")
    mtime = path.stat().st_mtime
    with _lock:
        if _cache.get("path") != str(path) or _cache.get("mtime") != mtime:
            _cache.update(path=str(path), mtime=mtime, predictor=PricePredictor.load(path))
            log.info("Loaded price model %s", _cache["predictor"].version)
        return _cache["predictor"]


def clear_cache():
    with _lock:
        _cache.clear()


def model_status() -> dict:
    try:
        p = get_predictor()
        return {"available": True, "version": p.version, "is_demo": p.is_demo}
    except ModelUnavailableError as e:
        return {"available": False, "reason": str(e)}


def load_history(crop_id: int, location_id: int, since: date | None = None) -> pd.DataFrame:
    q = select(MarketPrice.observation_date, MarketPrice.modal_price).where(
        MarketPrice.crop_id == crop_id, MarketPrice.location_id == location_id)
    if since:
        q = q.where(MarketPrice.observation_date >= since)
    rows = db.session.execute(q.order_by(MarketPrice.observation_date)).all()
    return pd.DataFrame([(r[0], float(r[1])) for r in rows], columns=["arrival_date", "modal_price"])
