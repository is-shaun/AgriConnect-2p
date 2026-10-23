"""Explicit request validation. Each function returns a clean dict containing ONLY the
whitelisted fields (protection against mass assignment) or raises ValidationError."""

from __future__ import annotations

import re
from datetime import date

from flask import request

from ..utils.errors import APIError, ValidationError

EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[A-Za-z]{2,}$")


def json_body() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise APIError("Request body must be a JSON object.", 400, "invalid_json")
    return data


def _reject_unknown(data: dict, allowed: set):
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise ValidationError({k: "This field is not allowed." for k in unknown})


def _text(data, key, errors, *, required=True, min_len=1, max_len=255):
    value = data.get(key)
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            errors[key] = "This field is required."
        return None
    if not isinstance(value, str):
        errors[key] = "Must be text."
        return None
    value = value.strip()
    if len(value) < min_len:
        errors[key] = f"Must be at least {min_len} characters."
    elif len(value) > max_len:
        errors[key] = f"Must be at most {max_len} characters."
    return value


def _email(data, key, errors, required=True):
    value = _text(data, key, errors, required=required, max_len=255)
    if value and not EMAIL_RE.match(value):
        errors[key] = "Enter a valid email address."
    return value.lower() if value else value


def _password(data, key, errors):
    value = data.get(key)
    if not isinstance(value, str) or not value:
        errors[key] = "This field is required."
        return None
    if len(value) < 8:
        errors[key] = "Must be at least 8 characters."
    elif len(value) > 128:
        errors[key] = "Must be at most 128 characters."
    elif not (re.search(r"[A-Za-z]", value) and re.search(r"\d", value)):
        errors[key] = "Must contain at least one letter and one number."
    return value


def _int(data, key, errors, *, required=True, minimum=1, maximum=None):
    value = data.get(key)
    if value is None or value == "":
        if required:
            errors[key] = "This field is required."
        return None
    if isinstance(value, bool):
        errors[key] = "Must be an integer."
        return None
    try:
        value = int(value)
        if isinstance(data.get(key), float) and data[key] != value:
            raise ValueError
    except (TypeError, ValueError):
        errors[key] = "Must be an integer."
        return None
    if value < minimum or (maximum is not None and value > maximum):
        errors[key] = f"Must be between {minimum} and {maximum}." if maximum else f"Must be at least {minimum}."
    return value


def validate_register(data):
    _reject_unknown(data, {"name", "email", "password"})
    errors = {}
    out = {"name": _text(data, "name", errors, min_len=2, max_len=100),
           "email": _email(data, "email", errors),
           "password": _password(data, "password", errors)}
    if errors:
        raise ValidationError(errors)
    return out


def validate_login(data):
    errors = {}
    out = {"email": _email(data, "email", errors)}
    if not isinstance(data.get("password"), str) or not data.get("password"):
        errors["password"] = "This field is required."
    out["password"] = data.get("password")
    if errors:
        raise ValidationError(errors)
    return out


def validate_profile_update(data):
    _reject_unknown(data, {"name", "email", "current_password", "new_password"})
    if not data:
        raise ValidationError({"_": "Provide at least one field to update."})
    errors, out = {}, {}
    if "name" in data:
        out["name"] = _text(data, "name", errors, min_len=2, max_len=100)
    if "email" in data:
        out["email"] = _email(data, "email", errors)
    if "new_password" in data:
        out["new_password"] = _password(data, "new_password", errors)
    if ("email" in data or "new_password" in data) and not data.get("current_password"):
        errors["current_password"] = "Enter your current password to change email or password."
    out["current_password"] = data.get("current_password")
    if errors:
        raise ValidationError(errors)
    return out


def validate_contact(data):
    _reject_unknown(data, {"name", "email", "subject", "message"})
    errors = {}
    out = {"name": _text(data, "name", errors, min_len=2, max_len=100),
           "email": _email(data, "email", errors),
           "subject": _text(data, "subject", errors, min_len=3, max_len=150),
           "message": _text(data, "message", errors, min_len=10, max_len=5000)}
    if errors:
        raise ValidationError(errors)
    return out


def validate_prediction(data, supported_horizons):
    _reject_unknown(data, {"crop_id", "location_id", "horizon_weeks"})
    errors = {}
    out = {"crop_id": _int(data, "crop_id", errors), "location_id": _int(data, "location_id", errors),
           "horizon_weeks": _int(data, "horizon_weeks", errors, maximum=52)}
    if out["horizon_weeks"] is not None and "horizon_weeks" not in errors and out["horizon_weeks"] not in supported_horizons:
        errors["horizon_weeks"] = f"Supported horizons are {', '.join(map(str, supported_horizons))} weeks."
    if errors:
        raise ValidationError(errors)
    return out


def query_int(name):
    raw = request.args.get(name)
    if raw in (None, ""):
        return None
    try:
        value = int(raw)
        if value < 1:
            raise ValueError
        return value
    except ValueError:
        raise ValidationError({name: "Must be a positive integer."})


def query_date(name):
    raw = request.args.get(name)
    if raw in (None, ""):
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise ValidationError({name: "Must be a date in YYYY-MM-DD format."})


def query_bool(name):
    raw = request.args.get(name)
    if raw in (None, ""):
        return None
    if raw.lower() in {"true", "1", "yes"}:
        return True
    if raw.lower() in {"false", "0", "no"}:
        return False
    raise ValidationError({name: "Must be true or false."})


def query_text(name, max_len=100):
    raw = (request.args.get(name) or "").strip()
    if len(raw) > max_len:
        raise ValidationError({name: f"Must be at most {max_len} characters."})
    return raw or None
