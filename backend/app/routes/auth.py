import logging

from flask import Blueprint, jsonify
from flask_jwt_extended import create_access_token, current_user, jwt_required, set_access_cookies, unset_jwt_cookies
from sqlalchemy import func, select

from ..extensions import db, jwt
from ..models import User
from ..schemas.validators import json_body, validate_login, validate_register
from ..utils.errors import APIError, ValidationError
from ..utils.rate_limit import rate_limit

bp = Blueprint("auth", __name__, url_prefix="/api/auth")
log = logging.getLogger(__name__)


@jwt.user_identity_loader
def _identity(user):
    return str(user.id)


@jwt.user_lookup_loader
def _lookup(_header, payload):
    try:
        return db.session.get(User, int(payload["sub"]))
    except (TypeError, ValueError):
        return None


def _session_response(user, status):
    resp = jsonify({"user": user.to_dict()})
    set_access_cookies(resp, create_access_token(identity=user))
    return resp, status


@bp.post("/register")
@rate_limit(10, 60, "auth")
def register():
    data = validate_register(json_body())
    exists = db.session.execute(select(User.id).where(func.lower(User.email) == data["email"])).first()
    if exists:
        raise ValidationError({"email": "An account with this email already exists."})
    user = User(name=data["name"], email=data["email"], role="user")  # role is never client-controlled
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()
    log.info("New user registered id=%s", user.id)
    return _session_response(user, 201)


@bp.post("/login")
@rate_limit(10, 60, "auth")
def login():
    data = validate_login(json_body())
    user = db.session.execute(select(User).where(func.lower(User.email) == data["email"])).scalar_one_or_none()
    if user is None or not user.check_password(data["password"]):
        raise APIError("Invalid email or password.", 401, "invalid_credentials")
    return _session_response(user, 200)


@bp.get("/me")
@jwt_required()
def me():
    return jsonify({"user": current_user.to_dict()})


@bp.post("/logout")
def logout():
    resp = jsonify({"message": "Logged out."})
    unset_jwt_cookies(resp)
    return resp
