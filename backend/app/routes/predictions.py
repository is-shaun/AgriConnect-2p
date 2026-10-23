import logging
from datetime import date, timedelta

import pandas as pd

from flask import Blueprint, jsonify
from flask_jwt_extended import current_user, jwt_required
from sqlalchemy import func, select

from ..extensions import db
from ..models import Crop, Location, MarketPrice, Prediction
from ..schemas.validators import json_body, validate_prediction
from ..services import prediction_service as ps
from ..utils.errors import APIError, NotFound
from ..utils.pagination import paginate
from ..utils.rate_limit import rate_limit

bp = Blueprint("predictions", __name__, url_prefix="/api/predictions")
log = logging.getLogger(__name__)
STALE_AFTER_DAYS = 30
HISTORY_WINDOW_DAYS = 26 * 7  # 26 weeks: enough for every feature plus the chart


@bp.get("/model")
def model_info():
    """Public description of the active model: horizons, supported series, validation metrics."""
    try:
        p = ps.get_predictor()
    except ps.ModelUnavailableError as e:
        return jsonify({"available": False, "reason": str(e), "horizons": []})
    m = p.metadata
    return jsonify({
        "available": True, "version": p.version, "model_name": m["model_name"], "is_demo": p.is_demo,
        "data_kind": m["data_kind"], "trained_at": m["trained_at"], "horizons": p.horizons,
        "horizon_unit": m["horizon_unit"], "min_history_weeks": m["min_history_weeks"],
        "test_metrics": {"mae": m["test"]["selected"]["mae"], "rmse": m["test"]["selected"]["rmse"],
                         "mape_pct": m["test"]["selected"]["mape_pct"],
                         "by_horizon": m["test"]["selected"]["by_horizon"],
                         "baseline_name": m["test"]["baseline_name"], "baseline_mae": m["test"]["baseline"]["mae"],
                         "mae_skill_vs_baseline": m["test"]["mae_skill_vs_baseline"]},
        "validation": {k: {"mae": v["mae"], "rmse": v["rmse"]} for k, v in m["validation"].items()},
        "training_period": {"from": m["training_data"]["date_min"], "to": m["training_data"]["date_max"]},
        "notes": m.get("notes"),
    })


@bp.post("")
@jwt_required()
@rate_limit(30, 60, "predict")
def create_prediction():
    data = json_body()
    try:
        predictor = ps.get_predictor()
    except ps.ModelUnavailableError as e:
        raise APIError(str(e), 503, "model_unavailable")
    v = validate_prediction(data, predictor.horizons)
    crop = db.session.get(Crop, v["crop_id"])
    if crop is None:
        raise NotFound("Crop not found.")
    loc = db.session.get(Location, v["location_id"])
    if loc is None:
        raise NotFound("Market not found.")
    if not predictor.supports(crop.name, loc.state, loc.district, loc.market_name):
        raise APIError(f"Predictions are not available for {crop.name} at {loc.market_name}: the current model "
                       "was not trained on this crop and market.", 422, "unsupported_series")
    last = db.session.scalar(select(func.max(MarketPrice.observation_date))
                             .where(MarketPrice.crop_id == crop.id, MarketPrice.location_id == loc.id))
    if last is None:
        raise APIError(f"There is no price history for {crop.name} at {loc.market_name}.", 422, "insufficient_history")
    history = ps.load_history(crop.id, loc.id, since=last - timedelta(days=HISTORY_WINDOW_DAYS))
    try:
        result = predictor.predict(history, crop.name, loc.state, loc.district, loc.market_name, v["horizon_weeks"])
    except ps.InsufficientHistoryError as e:
        raise APIError(str(e), 422, "insufficient_history")

    data_is_demo = bool(db.session.scalar(select(func.max(MarketPrice.is_demo)).where(
        MarketPrice.crop_id == crop.id, MarketPrice.location_id == loc.id,
        MarketPrice.observation_date >= last - timedelta(days=HISTORY_WINDOW_DAYS))))
    is_demo = result["is_demo_model"] or data_is_demo
    rng = result["typical_range"]
    pred = Prediction(
        user_id=current_user.id, crop_id=crop.id, location_id=loc.id, horizon_weeks=v["horizon_weeks"],
        base_date=date.fromisoformat(result["last_observation_date"]),
        prediction_date=date.fromisoformat(result["target_week_ending"]),
        base_price=result["base_price"], predicted_price=result["predicted_price"],
        range_low=rng["low"] if rng else None, range_high=rng["high"] if rng else None,
        model_version=result["model_version"], is_demo=is_demo)
    db.session.add(pred)
    db.session.commit()

    warnings = []
    if is_demo:
        warnings.append("Demo estimate: the model and/or the price history are synthetic demonstration data, "
                        "not real market prices. Do not use this for trading or farm decisions.")
    age = (date.today() - last).days
    if age > STALE_AFTER_DAYS:
        warnings.append(f"The latest available price is {age} days old, so this estimate may be outdated.")
    weekly = (history.assign(arrival_date=pd.to_datetime(history["arrival_date"]))
              .set_index("arrival_date")["modal_price"].resample("W-SUN").mean().dropna())
    history_points = [{"date": d.date().isoformat(), "modal_price": round(float(v), 2)} for d, v in weekly.items()]
    return jsonify({"prediction": pred.to_dict(), "details": result, "history": history_points,
                    "history_interval": "weekly mean modal price (week ending Sunday)",
                    "warnings": warnings,
                    "disclaimer": "Predictions are statistical estimates, not guaranteed future market prices."}), 201


@bp.get("")
@jwt_required()
def list_predictions():
    query = (db.session.query(Prediction).filter(Prediction.user_id == current_user.id)
             .order_by(Prediction.created_at.desc(), Prediction.id.desc()))
    return jsonify(paginate(query, Prediction.to_dict, default_per_page=10))


@bp.get("/<int:prediction_id>")
@jwt_required()
def get_prediction(prediction_id):
    pred = db.session.get(Prediction, prediction_id)
    # Same 404 for "missing" and "someone else's" so ids cannot be probed.
    if pred is None or pred.user_id != current_user.id:
        raise NotFound("Prediction not found.")
    return jsonify({"prediction": pred.to_dict()})
