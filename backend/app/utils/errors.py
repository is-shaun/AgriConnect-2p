"""Consistent JSON error responses: {"error": {"code", "message", "details"?}}."""

from __future__ import annotations

import logging

from flask import jsonify
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException

log = logging.getLogger(__name__)


class APIError(Exception):
    def __init__(self, message: str, status: int = 400, code: str = "bad_request", details=None):
        super().__init__(message)
        self.message, self.status, self.code, self.details = message, status, code, details


class ValidationError(APIError):
    def __init__(self, details: dict, message: str = "Some fields are invalid."):
        super().__init__(message, 422, "validation_error", details)


class NotFound(APIError):
    def __init__(self, message: str = "Resource not found."):
        super().__init__(message, 404, "not_found")


def error_response(message, status, code, details=None):
    body = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return jsonify(body), status


def register_error_handlers(app, jwt):
    from ..extensions import db

    @app.errorhandler(APIError)
    def _api_error(e: APIError):
        return error_response(e.message, e.status, e.code, e.details)

    @app.errorhandler(HTTPException)
    def _http_error(e: HTTPException):
        code = (e.name or "error").lower().replace(" ", "_")
        return error_response(e.description or e.name, e.code or 500, code)

    @app.errorhandler(SQLAlchemyError)
    def _db_error(e):
        db.session.rollback()
        log.exception("Database error")
        return error_response("A database error occurred. Please try again.", 500, "database_error")

    @app.errorhandler(Exception)
    def _unhandled(e):
        log.exception("Unhandled error")
        return error_response("An unexpected error occurred.", 500, "internal_error")

    @jwt.unauthorized_loader
    def _missing(reason):
        if "csrf" in (reason or "").lower():
            return error_response("Missing security token. Please refresh the page and try again.", 401, "csrf_missing")
        return error_response("Please log in to continue.", 401, "unauthorized")

    @jwt.invalid_token_loader
    def _invalid(reason):
        return error_response("Your session is invalid. Please log in again.", 401, "invalid_token")

    @jwt.expired_token_loader
    def _expired(header, payload):
        return error_response("Your session has expired. Please log in again.", 401, "token_expired")

    @jwt.user_lookup_error_loader
    def _user_missing(header, payload):
        return error_response("Account not found. Please log in again.", 401, "invalid_token")
