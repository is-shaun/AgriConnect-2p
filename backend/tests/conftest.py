"""Shared fixtures.

Tests run against in-memory SQLite by default so they need no server. To run the same
suite against MySQL, create an empty test database and set TEST_DATABASE_URL, e.g.

    TEST_DATABASE_URL="mysql+pymysql://agri_test:pw@localhost:3306/agriconnect_test" pytest
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "ml"))

from app import create_app  # noqa: E402
from app.extensions import db as _db  # noqa: E402
from app.services import prediction_service  # noqa: E402
from app.services.importer import import_prices  # noqa: E402
from app.services.providers import CsvFileProvider  # noqa: E402
from app.utils.rate_limit import reset_rate_limits  # noqa: E402

DEMO_CSV = ROOT / "ml" / "data" / "demo_market_prices.csv"
SERIES = [("Onion", "Lasalgaon"), ("Wheat", "Patna"), ("Tomato", "Patna"), ("Mustard", "Indore")]


@pytest.fixture(scope="session")
def subset_csv(tmp_path_factory):
    df = pd.read_csv(DEMO_CSV)
    keep = pd.Series(False, index=df.index)
    for crop, market in SERIES:
        keep |= (df.commodity == crop) & (df.market == market)
    path = tmp_path_factory.mktemp("data") / "subset.csv"
    df[keep].to_csv(path, index=False)
    return path


@pytest.fixture(scope="session")
def model_path(subset_csv, tmp_path_factory):
    import train as train_module

    out = tmp_path_factory.mktemp("model") / "price_model.joblib"
    train_module.train(subset_csv, out, quiet=True)
    return out


@pytest.fixture()
def app(model_path):
    app = create_app("testing", {"MODEL_PATH": str(model_path)})
    with app.app_context():
        _db.drop_all()
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()
    prediction_service.clear_cache()
    reset_rate_limits()


@pytest.fixture()
def seeded(app, subset_csv):
    import_prices(CsvFileProvider(subset_csv, is_demo=True))
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


def csrf_headers(client):
    cookie = client.get_cookie("csrf_access_token")
    return {"X-CSRF-TOKEN": cookie.value} if cookie else {}


@pytest.fixture()
def register(client):
    def _register(email="farmer@example.com", password="harvest2026", name="Asha Devi"):
        return client.post("/api/auth/register", json={"name": name, "email": email, "password": password})
    return _register


@pytest.fixture()
def auth_client(client, register):
    resp = register()
    assert resp.status_code == 201, resp.get_json()
    return client
