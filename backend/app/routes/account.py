"""User profile, contact form and health check."""

import logging

from flask import Blueprint, jsonify
from flask_jwt_extended import current_user, jwt_required
from sqlalchemy import func, select, text

from ..extensions import db
from ..models import ContactMessage, User
from ..schemas.validators import json_body, validate_contact, validate_profile_update
from ..services.prediction_service import model_status
from ..utils.errors import ValidationError
from ..utils.rate_limit import rate_limit

bp = Blueprint("account", __name__, url_prefix="/api")
log = logging.getLogger(__name__)


@bp.get("/users/me")
@jwt_required()
def get_me():
    u = current_user
    return jsonify({"user": u.to_dict(), "stats": {"predictions": u.predictions.count()}})


@bp.patch("/users/me")
@jwt_required()
@rate_limit(20, 60, "profile")
def update_me():
    data = validate_profile_update(json_body())
    u = current_user
    if ("email" in data or "new_password" in data) and not u.check_password(data["current_password"] or ""):
        raise ValidationError({"current_password": "Current password is incorrect."})
    if "name" in data:
        u.name = data["name"]
    if "email" in data and data["email"] != u.email:
        taken = db.session.execute(select(User.id).where(func.lower(User.email) == data["email"], User.id != u.id)).first()
        if taken:
            raise ValidationError({"email": "An account with this email already exists."})
        u.email = data["email"]
    if data.get("new_password"):
        u.set_password(data["new_password"])
    db.session.commit()
    return jsonify({"user": u.to_dict()})


@bp.post("/contact")
@rate_limit(5, 300, "contact")
def contact():
    data = validate_contact(json_body())
    msg = ContactMessage(**data)
    db.session.add(msg)
    db.session.commit()
    log.info("Contact message stored id=%s", msg.id)
    return jsonify({"message": "Thanks! Your message has been received.", "id": msg.id}), 201


@bp.get("/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))
        database = {"ok": True}
    except Exception as e:  # pragma: no cover - depends on infrastructure
        db.session.rollback()
        log.warning("Health check DB failure: %s", e.__class__.__name__)
        database = {"ok": False}
    body = {"status": "ok" if database["ok"] else "degraded", "database": database, "model": model_status()}
    return jsonify(body), 200 if database["ok"] else 503
