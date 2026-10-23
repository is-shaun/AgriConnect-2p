import pytest
from sqlalchemy import inspect
from sqlalchemy.dialects import mysql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateTable

from app.extensions import db
from app.models import ContactMessage, Crop, Location, MarketPrice, User
from app.services.importer import import_prices
from app.services.providers import CsvFileProvider
from tests.conftest import csrf_headers


# ---------------------------------------------------------------- profile
def test_get_and_update_profile(auth_client):
    me = auth_client.get("/api/users/me").get_json()
    assert me["user"]["name"] == "Asha Devi" and me["stats"]["predictions"] == 0
    resp = auth_client.patch("/api/users/me", json={"name": "Asha D."}, headers=csrf_headers(auth_client))
    assert resp.status_code == 200 and resp.get_json()["user"]["name"] == "Asha D."


def test_profile_cannot_escalate_role(auth_client):
    resp = auth_client.patch("/api/users/me", json={"role": "admin"}, headers=csrf_headers(auth_client))
    assert resp.status_code == 422
    assert db.session.query(User).one().role == "user"


def test_changing_email_or_password_requires_current_password(auth_client, register):
    h = csrf_headers(auth_client)
    assert auth_client.patch("/api/users/me", json={"email": "new@example.com"}, headers=h).status_code == 422
    wrong = auth_client.patch("/api/users/me", json={"email": "new@example.com", "current_password": "nope12345"},
                              headers=h)
    assert wrong.get_json()["error"]["details"]["current_password"] == "Current password is incorrect."
    ok = auth_client.patch("/api/users/me", json={"new_password": "newharvest99", "current_password": "harvest2026"},
                           headers=h)
    assert ok.status_code == 200
    auth_client.post("/api/auth/logout")
    assert auth_client.post("/api/auth/login",
                            json={"email": "farmer@example.com", "password": "newharvest99"}).status_code == 200


def test_profile_email_must_be_unique(client, register):
    register(email="taken@example.com")
    client.post("/api/auth/logout")
    register(email="me@example.com")
    resp = client.patch("/api/users/me", json={"email": "taken@example.com", "current_password": "harvest2026"},
                        headers=csrf_headers(client))
    assert resp.status_code == 422 and "email" in resp.get_json()["error"]["details"]


def test_profile_requires_auth(client):
    assert client.get("/api/users/me").status_code == 401


# ---------------------------------------------------------------- contact
def test_contact_success(app, client):
    resp = client.post("/api/contact", json={"name": "Ravi", "email": "ravi@example.com",
                                             "subject": "Mandi data", "message": "Please add Gaya market prices."})
    assert resp.status_code == 201
    assert db.session.query(ContactMessage).one().subject == "Mandi data"


def test_contact_validation(app, client):
    resp = client.post("/api/contact", json={"name": "", "email": "bad", "subject": "Hi", "message": "short"})
    assert resp.status_code == 422
    assert set(resp.get_json()["error"]["details"]) == {"name", "email", "subject", "message"}
    assert db.session.query(ContactMessage).count() == 0


# ---------------------------------------------------------------- database / import
def test_database_initialisation_creates_all_tables(app):
    tables = set(inspect(db.engine).get_table_names())
    assert {"users", "crops", "locations", "market_prices", "predictions", "contact_messages"} <= tables


def test_schema_compiles_for_mysql(app):
    ddl = str(CreateTable(MarketPrice.__table__).compile(dialect=mysql.dialect()))
    assert "NUMERIC(12, 2)" in ddl or "DECIMAL(12, 2)" in ddl
    assert "uq_price_observation" in ddl and "FOREIGN KEY(crop_id)" in ddl


def test_price_constraints_enforced(app):
    crop = Crop(name="Test", category="X"); loc = Location(state="S", district="D", market_name="M")
    db.session.add_all([crop, loc]); db.session.commit()
    from datetime import date
    db.session.add(MarketPrice(crop_id=crop.id, location_id=loc.id, observation_date=date(2026, 1, 1),
                               min_price=10, max_price=5, modal_price=7, source="t"))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


CSV_HEADER = "state,district,market,commodity,category,unit,arrival_date,min_price,max_price,modal_price,source\n"


def test_import_validates_rows_and_is_idempotent(app, tmp_path):
    f = tmp_path / "prices.csv"
    f.write_text(CSV_HEADER +
                 "Bihar,Gaya,Gaya,Wheat,Cereals,Rs/quintal,2026-10-01,2300,2500,2400,Agmarknet export\n"
                 "Bihar,Gaya,Gaya,Wheat,Cereals,Rs/quintal,02/10/2026,2310,2510,2420,Agmarknet export\n"
                 "Bihar,Gaya,Gaya,Wheat,Cereals,Rs/quintal,2026-13-01,2300,2500,2400,x\n"
                 "Bihar,Gaya,Gaya,Wheat,Cereals,Rs/quintal,2026-10-03,2600,2500,2400,x\n"
                 "Bihar,Gaya,Gaya,Wheat,Cereals,Rs/quintal,2026-10-04,abc,2500,2400,x\n"
                 ",Gaya,Gaya,Wheat,Cereals,Rs/quintal,2026-10-05,1,2,1,x\n"
                 "Bihar,Gaya,Gaya,Wheat,Cereals,Rs/quintal,2026-10-01,1,2,1,dup\n")
    report = import_prices(CsvFileProvider(f))
    assert report.inserted == 2 and report.crops_created == 1 and report.locations_created == 1
    assert sorted({e["row"] for e in report.errors}) == [4, 5, 6, 7, 8]
    rows = db.session.query(MarketPrice).all()
    assert all(not r.is_demo and r.source == "Agmarknet export" for r in rows)
    again = import_prices(CsvFileProvider(f))
    assert again.inserted == 0 and again.skipped_duplicates == 2


def test_import_dry_run_and_update(app, tmp_path):
    f = tmp_path / "p.csv"
    f.write_text(CSV_HEADER + "Bihar,Gaya,Gaya,Wheat,Cereals,Rs/quintal,2026-10-01,2300,2500,2400,src\n")
    assert import_prices(CsvFileProvider(f), dry_run=True).inserted == 1
    assert db.session.query(MarketPrice).count() == 0
    import_prices(CsvFileProvider(f))
    f.write_text(CSV_HEADER + "Bihar,Gaya,Gaya,Wheat,Cereals,Rs/quintal,2026-10-01,2300,2600,2450,src2\n")
    rep = import_prices(CsvFileProvider(f), on_duplicate="update")
    assert rep.updated == 1 and float(db.session.query(MarketPrice).one().modal_price) == 2450


def test_import_missing_columns(app, tmp_path):
    f = tmp_path / "bad.csv"
    f.write_text("state,market\nBihar,Gaya\n")
    rep = import_prices(CsvFileProvider(f))
    assert rep.inserted == 0 and "Missing required column" in rep.errors[0]["message"]


def test_cli_init_and_seed(app, subset_csv):
    runner = app.test_cli_runner()
    assert "ready" in runner.invoke(args=["init-db"]).output
    out = runner.invoke(args=["seed-demo", "--csv", str(subset_csv)]).output
    assert "inserted=" in out and db.session.query(MarketPrice).filter_by(is_demo=True).count() > 0
    second = runner.invoke(args=["seed-demo", "--csv", str(subset_csv)]).output
    assert "inserted=0" in second
