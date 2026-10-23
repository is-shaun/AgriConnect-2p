from datetime import date

import pytest

from app.extensions import db
from app.models import Crop, Location, MarketPrice
from app.services import prediction_service
from tests.conftest import csrf_headers


def _ids(client, crop, market):
    crop_id = next(c["id"] for c in client.get("/api/crops").get_json()["items"] if c["name"] == crop)
    loc_id = next(m["id"] for m in client.get("/api/markets").get_json()["items"] if m["market_name"] == market)
    return crop_id, loc_id


def _predict(client, payload):
    return client.post("/api/predictions", json=payload, headers=csrf_headers(client))


def test_model_info_is_public(app, client):
    info = client.get("/api/predictions/model").get_json()
    assert info["available"] and info["is_demo"] and info["horizons"] == [1, 2, 4]
    assert info["test_metrics"]["mae"] > 0 and "baseline_mae" in info["test_metrics"]


def test_prediction_requires_login(seeded, client):
    assert client.post("/api/predictions", json={}).status_code == 401
    assert client.get("/api/predictions").status_code == 401


def test_successful_prediction_is_model_generated_and_labelled_demo(seeded, auth_client):
    crop_id, loc_id = _ids(auth_client, "Onion", "Lasalgaon")
    resp = _predict(auth_client, {"crop_id": crop_id, "location_id": loc_id, "horizon_weeks": 2})
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    p, d = body["prediction"], body["details"]
    assert p["predicted_price"] > 0 and p["unit"] == "Rs/quintal" and p["horizon_weeks"] == 2
    assert p["is_demo"] is True and any("Demo estimate" in w for w in body["warnings"])
    assert p["model_version"].endswith("-demo")
    assert d["target_week_ending"] == "2026-11-01" and d["last_observation_date"] == "2026-10-16"
    assert d["typical_range"]["low"] < p["predicted_price"] < d["typical_range"]["high"]
    assert len(body["history"]) >= 13 and "estimates" in body["disclaimer"]

    # Same inputs -> same output (deterministic pipeline), and history is stored per user.
    again = _predict(auth_client, {"crop_id": crop_id, "location_id": loc_id, "horizon_weeks": 2}).get_json()
    assert again["prediction"]["predicted_price"] == p["predicted_price"]
    listing = auth_client.get("/api/predictions").get_json()
    assert listing["pagination"]["total"] == 2
    assert auth_client.get(f"/api/predictions/{p['id']}").get_json()["prediction"]["id"] == p["id"]


def test_prediction_matches_offline_pipeline(seeded, auth_client, model_path, subset_csv):
    """The API must use exactly the same features/model as the ML scripts."""
    from agriml.data import load_price_csv
    from agriml.predictor import PricePredictor

    df, _ = load_price_csv(subset_csv)
    hist = df[(df.commodity == "Wheat") & (df.market == "Patna")][["arrival_date", "modal_price"]]
    offline = PricePredictor.load(model_path).predict(hist, "Wheat", "Bihar", "Patna", "Patna", 4)
    crop_id, loc_id = _ids(auth_client, "Wheat", "Patna")
    api = _predict(auth_client, {"crop_id": crop_id, "location_id": loc_id, "horizon_weeks": 4}).get_json()
    assert api["details"]["predicted_price"] == pytest.approx(offline["predicted_price"], rel=1e-6)


def test_users_cannot_read_each_others_predictions(seeded, client, register):
    register(email="a@example.com")
    crop_id, loc_id = _ids(client, "Onion", "Lasalgaon")
    pid = _predict(client, {"crop_id": crop_id, "location_id": loc_id, "horizon_weeks": 1}).get_json()["prediction"]["id"]
    client.post("/api/auth/logout")
    register(email="b@example.com")
    assert client.get(f"/api/predictions/{pid}").status_code == 404
    assert client.get("/api/predictions").get_json()["pagination"]["total"] == 0


@pytest.mark.parametrize("payload,field", [
    ({}, "crop_id"),
    ({"crop_id": "x", "location_id": 1, "horizon_weeks": 1}, "crop_id"),
    ({"crop_id": 1, "location_id": 1, "horizon_weeks": 3}, "horizon_weeks"),
    ({"crop_id": 1, "location_id": 1, "horizon_weeks": 0}, "horizon_weeks"),
    ({"crop_id": 1, "location_id": 1, "horizon_weeks": True}, "horizon_weeks"),
    ({"crop_id": 1, "location_id": 1, "horizon_weeks": 1, "predicted_price": 5}, "predicted_price"),
])
def test_prediction_input_validation(seeded, auth_client, payload, field):
    resp = _predict(auth_client, payload)
    assert resp.status_code == 422
    assert field in resp.get_json()["error"]["details"]


def test_unknown_crop_or_market(seeded, auth_client):
    crop_id, loc_id = _ids(auth_client, "Onion", "Lasalgaon")
    assert _predict(auth_client, {"crop_id": 999, "location_id": loc_id, "horizon_weeks": 1}).status_code == 404
    assert _predict(auth_client, {"crop_id": crop_id, "location_id": 999, "horizon_weeks": 1}).status_code == 404


def test_unsupported_series_is_refused_not_fabricated(seeded, auth_client):
    crop_id, loc_id = _ids(auth_client, "Onion", "Patna")  # Onion is not traded at Patna in the subset
    resp = _predict(auth_client, {"crop_id": crop_id, "location_id": loc_id, "horizon_weeks": 1})
    assert resp.status_code == 422 and resp.get_json()["error"]["code"] == "unsupported_series"


def test_insufficient_history(seeded, auth_client):
    crop_id, loc_id = _ids(auth_client, "Onion", "Lasalgaon")
    db.session.query(MarketPrice).filter(MarketPrice.crop_id == crop_id,
                                         MarketPrice.observation_date < date(2026, 9, 1)).delete()
    db.session.commit()
    resp = _predict(auth_client, {"crop_id": crop_id, "location_id": loc_id, "horizon_weeks": 1})
    assert resp.status_code == 422 and resp.get_json()["error"]["code"] == "insufficient_history"


def test_supported_series_without_any_rows(app, auth_client):
    crop = Crop(name="Onion", category="Vegetables", unit="Rs/quintal")
    loc = Location(state="Maharashtra", district="Nashik", market_name="Lasalgaon")
    db.session.add_all([crop, loc]); db.session.commit()
    resp = _predict(auth_client, {"crop_id": crop.id, "location_id": loc.id, "horizon_weeks": 1})
    assert resp.status_code == 422 and resp.get_json()["error"]["code"] == "insufficient_history"


def test_missing_model_returns_503(seeded, auth_client, app, tmp_path):
    app.config["MODEL_PATH"] = str(tmp_path / "nope.joblib")
    prediction_service.clear_cache()
    crop_id, loc_id = _ids(auth_client, "Onion", "Lasalgaon")
    resp = _predict(auth_client, {"crop_id": crop_id, "location_id": loc_id, "horizon_weeks": 1})
    assert resp.status_code == 503 and resp.get_json()["error"]["code"] == "model_unavailable"
    assert auth_client.get("/api/predictions/model").get_json()["available"] is False
    assert auth_client.get("/api/health").get_json()["model"]["available"] is False


def test_corrupt_model_returns_503(seeded, auth_client, app, tmp_path):
    bad = tmp_path / "bad.joblib"
    bad.write_bytes(b"not a model")
    app.config["MODEL_PATH"] = str(bad)
    prediction_service.clear_cache()
    crop_id, loc_id = _ids(auth_client, "Onion", "Lasalgaon")
    assert _predict(auth_client, {"crop_id": crop_id, "location_id": loc_id, "horizon_weeks": 1}).status_code == 503
