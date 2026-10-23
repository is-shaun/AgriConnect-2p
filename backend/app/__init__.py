"""AgriConnect Flask application factory."""

from __future__ import annotations

import logging
import os

import click
from flask import Flask

from config import CONFIGS, PROJECT_ROOT, validate_config

from .extensions import cors, db, jwt, migrate
from .utils.errors import register_error_handlers

DEMO_CSV = PROJECT_ROOT / "ml" / "data" / "demo_market_prices.csv"


def create_app(config_name: str | None = None, overrides: dict | None = None) -> Flask:
    config_name = config_name or os.getenv("APP_ENV", "development")
    app = Flask(__name__)
    app.config.from_object(CONFIGS[config_name])
    app.config["APP_ENV"] = config_name
    if overrides:
        app.config.update(overrides)
    validate_config(app.config)
    app.json.sort_keys = False

    logging.basicConfig(level=app.config["LOG_LEVEL"], format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    db.init_app(app)
    migrate.init_app(app, db, directory=str(PROJECT_ROOT / "backend" / "migrations"))
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}}, supports_credentials=True)

    from . import models  # noqa: F401  (register models with SQLAlchemy)
    from .routes import account, auth, catalog, predictions

    for bp in (auth.bp, catalog.bp, predictions.bp, account.bp):
        app.register_blueprint(bp)
    register_error_handlers(app, jwt)

    @app.after_request
    def _security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault("Cache-Control", "no-store")
        return resp

    register_cli(app)
    return app


def register_cli(app: Flask) -> None:
    @app.cli.command("init-db")
    @click.option("--drop", is_flag=True, help="Drop all tables first (destroys data).")
    def init_db(drop):
        """Create all tables (idempotent)."""
        if drop:
            db.drop_all()
        db.create_all()
        click.echo("Database tables are ready.")

    @app.cli.command("seed-demo")
    @click.option("--csv", "csv_path", default=str(DEMO_CSV), show_default=True)
    def seed_demo(csv_path):
        """Load the clearly labelled SYNTHETIC demo prices."""
        from .services.importer import import_prices
        from .services.providers import CsvFileProvider

        db.create_all()
        report = import_prices(CsvFileProvider(csv_path, is_demo=True))
        click.echo(f"Demo seed: inserted={report.inserted} skipped={report.skipped_duplicates} "
                   f"crops+={report.crops_created} markets+={report.locations_created} errors={len(report.errors)}")

    @app.cli.command("import-prices")
    @click.argument("csv_path")
    @click.option("--dry-run", is_flag=True)
    @click.option("--on-duplicate", type=click.Choice(["skip", "update"]), default="skip")
    @click.option("--demo", is_flag=True, help="Mark the imported rows as demo data.")
    def import_cmd(csv_path, dry_run, on_duplicate, demo):
        """Validate and import a market-price CSV."""
        from .services.importer import import_prices
        from .services.providers import CsvFileProvider

        report = import_prices(CsvFileProvider(csv_path, is_demo=demo), dry_run=dry_run, on_duplicate=on_duplicate)
        d = report.to_dict(max_errors=20)
        for e in d["errors"]:
            click.echo(f"  line {e['row']}: {e['field']}: {e['message']}")
        click.echo({k: v for k, v in d.items() if k != "errors"})
