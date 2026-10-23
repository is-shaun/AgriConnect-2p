"""Validate and import market-price records into the database."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

import pandas as pd
from sqlalchemy import select

from ..extensions import db
from ..models import Crop, Location, MarketPrice, utcnow
from .providers import PriceProvider

log = logging.getLogger(__name__)
REQUIRED = ["state", "district", "market", "commodity", "arrival_date", "min_price", "max_price", "modal_price"]
MAX_PRICE = Decimal("1000000")

CROP_DESCRIPTIONS = {
    "Wheat": "Rabi cereal and India's main staple grain after rice; procured at MSP in major producing states.",
    "Paddy (Common)": "Unmilled rice, the principal kharif cereal, traded in mandis before milling.",
    "Maize": "Versatile kharif and rabi cereal used for food, poultry feed and starch.",
    "Onion": "Key vegetable crop with pronounced seasonal price swings; Lasalgaon is Asia's largest onion market.",
    "Tomato": "Highly perishable vegetable whose prices react sharply to weather and arrivals.",
    "Potato": "Staple vegetable, largely stored in cold storage, with prices tied to storage release.",
    "Mustard": "Major rabi oilseed (rapeseed-mustard) grown widely in Rajasthan, UP and MP.",
    "Bengal Gram (Chana)": "India's largest pulse crop by production, sown in the rabi season.",
}


@dataclass
class ImportReport:
    rows_read: int = 0
    valid_rows: int = 0
    inserted: int = 0
    updated: int = 0
    skipped_duplicates: int = 0
    crops_created: int = 0
    locations_created: int = 0
    errors: list = field(default_factory=list)

    def to_dict(self, max_errors=50):
        d = self.__dict__.copy()
        d["error_count"] = len(self.errors)
        d["errors"] = self.errors[:max_errors]
        return d


def _dec(v):
    try:
        d = Decimal(str(v).strip().replace(",", ""))
        return d if d.is_finite() else None
    except (InvalidOperation, AttributeError):
        return None


def validate_rows(df: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    """Return (valid_records, errors). Row numbers refer to the CSV line (header = line 1)."""
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        return [], [{"row": 1, "field": ",".join(missing), "message": "Missing required column(s)."}]
    valid, errors, seen = [], [], set()
    for i, r in enumerate(df.to_dict("records"), start=2):
        row_errors = []

        def text(key, max_len):
            v = r.get(key)
            v = "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v).strip()
            if not v and key in REQUIRED:
                row_errors.append((key, "Required."))
            elif len(v) > max_len:
                row_errors.append((key, f"Longer than {max_len} characters."))
            return v

        rec = {"state": text("state", 80), "district": text("district", 80), "market": text("market", 120),
               "commodity": text("commodity", 100), "category": text("category", 60) or "Uncategorised",
               "unit": text("unit", 30) or "Rs/quintal", "source": text("source", 255) or "unspecified"}
        raw_date = text("arrival_date", 20)
        dt = pd.to_datetime(raw_date, format="%Y-%m-%d", errors="coerce")
        if pd.isna(dt):
            dt = pd.to_datetime(raw_date, format="%d/%m/%Y", errors="coerce")
        if pd.isna(dt) and raw_date:
            row_errors.append(("arrival_date", "Use YYYY-MM-DD or DD/MM/YYYY."))
        rec["observation_date"] = None if pd.isna(dt) else dt.date()
        for key in ("min_price", "max_price", "modal_price"):
            v = _dec(r.get(key))
            if v is None:
                row_errors.append((key, "Must be a number."))
            elif v <= 0 or v > MAX_PRICE:
                row_errors.append((key, "Must be greater than 0 and at most 1,000,000."))
            rec[key] = v.quantize(Decimal("0.01")) if v is not None else None
        if not row_errors and not (rec["min_price"] <= rec["modal_price"] <= rec["max_price"]):
            row_errors.append(("modal_price", "Must satisfy min_price <= modal_price <= max_price."))
        key = (rec["commodity"].lower(), rec["state"].lower(), rec["district"].lower(), rec["market"].lower(),
               rec["observation_date"])
        if not row_errors and key in seen:
            row_errors.append(("arrival_date", "Duplicate of an earlier row in this file."))
        if row_errors:
            errors.extend({"row": i, "field": f, "message": m} for f, m in row_errors)
        else:
            seen.add(key)
            valid.append(rec)
    return valid, errors


def _get_or_create_crop(name, category, unit, cache, report):
    k = name.lower()
    if k not in cache:
        crop = db.session.execute(select(Crop).where(Crop.name == name)).scalar_one_or_none()
        if crop is None:
            crop = Crop(name=name, category=category, unit=unit, description=CROP_DESCRIPTIONS.get(name))
            db.session.add(crop)
            db.session.flush()
            report.crops_created += 1
        cache[k] = crop
    return cache[k]


def _get_or_create_location(state, district, market, cache, report):
    k = (state.lower(), district.lower(), market.lower())
    if k not in cache:
        loc = db.session.execute(select(Location).where(
            Location.state == state, Location.district == district, Location.market_name == market)).scalar_one_or_none()
        if loc is None:
            loc = Location(state=state, district=district, market_name=market)
            db.session.add(loc)
            db.session.flush()
            report.locations_created += 1
        cache[k] = loc
    return cache[k]


def import_prices(provider: PriceProvider, *, dry_run=False, on_duplicate="skip", batch_size=2000) -> ImportReport:
    """Import rows from a provider. Invalid rows are reported and never written.

    on_duplicate: "skip" keeps existing rows; "update" overwrites prices of existing rows.
    The whole import runs in one transaction; dry_run validates and rolls back.
    """
    if on_duplicate not in {"skip", "update"}:
        raise ValueError("on_duplicate must be 'skip' or 'update'")
    report = ImportReport()
    df = provider.fetch()
    report.rows_read = len(df)
    records, report.errors = validate_rows(df)
    report.valid_rows = len(records)
    crops, locations = {}, {}
    try:
        pending = []
        groups = {}
        for rec in records:
            crop = _get_or_create_crop(rec["commodity"], rec["category"], rec["unit"], crops, report)
            loc = _get_or_create_location(rec["state"], rec["district"], rec["market"], locations, report)
            groups.setdefault((crop.id, loc.id), []).append(rec)
        for (crop_id, loc_id), recs in groups.items():
            existing = {p.observation_date: p for p in db.session.execute(
                select(MarketPrice).where(MarketPrice.crop_id == crop_id, MarketPrice.location_id == loc_id)
            ).scalars()}
            for rec in recs:
                cur = existing.get(rec["observation_date"])
                if cur is not None:
                    if on_duplicate == "update":
                        cur.min_price, cur.max_price, cur.modal_price = rec["min_price"], rec["max_price"], rec["modal_price"]
                        cur.source, cur.is_demo = rec["source"], provider.is_demo
                        report.updated += 1
                    else:
                        report.skipped_duplicates += 1
                    continue
                pending.append({"crop_id": crop_id, "location_id": loc_id, "observation_date": rec["observation_date"],
                                "min_price": rec["min_price"], "max_price": rec["max_price"],
                                "modal_price": rec["modal_price"], "source": rec["source"],
                                "is_demo": provider.is_demo, "created_at": utcnow()})
        for start in range(0, len(pending), batch_size):
            db.session.execute(MarketPrice.__table__.insert(), pending[start:start + batch_size])
        report.inserted = len(pending)
        if dry_run:
            db.session.rollback()
        else:
            db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    log.info("Import from %s: %s", provider.name, {k: v for k, v in report.to_dict().items() if k != "errors"})
    return report
