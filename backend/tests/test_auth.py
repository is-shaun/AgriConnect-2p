from app.extensions import db
from app.models import User
from tests.conftest import csrf_headers


def test_register_creates_user_with_hashed_password_and_session(client, register):
    resp = register()
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["user"]["email"] == "farmer@example.com"
    assert body["user"]["role"] == "user"
    assert "password" not in str(body) and "password_hash" not in body["user"]
    user = db.session.query(User).one()
    assert user.password_hash != "harvest2026" and user.password_hash.startswith("scrypt:")
    # HttpOnly session cookie + readable CSRF cookie
    set_cookies = resp.headers.getlist("Set-Cookie")
    assert any(c.startswith("access_token_cookie=") and "HttpOnly" in c for c in set_cookies)
    assert any(c.startswith("csrf_access_token=") for c in set_cookies)
    assert client.get("/api/auth/me").status_code == 200


def test_register_rejects_duplicate_email_case_insensitively(client, register):
    register()
    resp = register(email="Farmer@Example.com")
    assert resp.status_code == 422
    assert "email" in resp.get_json()["error"]["details"]


def test_register_validation_errors(client):
    resp = client.post("/api/auth/register", json={"name": "A", "email": "nope", "password": "short"})
    assert resp.status_code == 422
    details = resp.get_json()["error"]["details"]
    assert set(details) == {"name", "email", "password"}


def test_register_rejects_role_mass_assignment(client):
    resp = client.post("/api/auth/register",
                       json={"name": "Eve", "email": "eve@example.com", "password": "harvest2026", "role": "admin"})
    assert resp.status_code == 422
    assert "role" in resp.get_json()["error"]["details"]
    assert db.session.query(User).count() == 0


def test_register_requires_json_object(client):
    resp = client.post("/api/auth/register", data="not json", content_type="text/plain")
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "invalid_json"


def test_login_success_and_invalid_credentials(client, register):
    register()
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401
    bad = client.post("/api/auth/login", json={"email": "farmer@example.com", "password": "wrongpass1"})
    assert bad.status_code == 401
    assert bad.get_json()["error"]["code"] == "invalid_credentials"
    unknown = client.post("/api/auth/login", json={"email": "ghost@example.com", "password": "wrongpass1"})
    assert unknown.get_json()["error"]["message"] == bad.get_json()["error"]["message"]  # no user enumeration
    ok = client.post("/api/auth/login", json={"email": "FARMER@example.com", "password": "harvest2026"})
    assert ok.status_code == 200
    assert client.get("/api/auth/me").get_json()["user"]["name"] == "Asha Devi"


def test_login_validation(client):
    resp = client.post("/api/auth/login", json={"email": "", "password": ""})
    assert resp.status_code == 422


def test_me_requires_auth(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
    assert resp.get_json()["error"]["code"] == "unauthorized"


def test_state_changing_request_requires_csrf_token(auth_client):
    no_csrf = auth_client.patch("/api/users/me", json={"name": "New Name"})
    assert no_csrf.status_code == 401
    assert no_csrf.get_json()["error"]["code"] == "csrf_missing"
    ok = auth_client.patch("/api/users/me", json={"name": "New Name"}, headers=csrf_headers(auth_client))
    assert ok.status_code == 200


def test_tampered_token_is_rejected(client):
    client.set_cookie("access_token_cookie", "not.a.jwt", path="/api/")
    resp = client.get("/api/auth/me")
    assert resp.status_code in (401, 422)


def test_rate_limit_on_login(app, client):
    app.config["RATE_LIMIT_ENABLED"] = True
    codes = [client.post("/api/auth/login", json={"email": "x@example.com", "password": "abc12345"}).status_code
             for _ in range(11)]
    assert codes[:10] == [401] * 10
    assert codes[10] == 429
