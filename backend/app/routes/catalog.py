"""Crops, markets, prices and summary statistics (all public, read-only)."""

from flask import Blueprint, jsonify, request
from sqlalchemy import distinct, func, or_, select

from ..extensions import db
from ..models import Crop, Location, MarketPrice, Prediction
from ..schemas.validators import query_bool, query_date, query_int, query_text
from ..utils.errors import NotFound, ValidationError
from ..utils.pagination import get_sort, paginate

bp = Blueprint("catalog", __name__, url_prefix="/api")


def _latest_snapshot(crop_id=None):
    """Latest observation per (crop, location)."""
    latest = (select(MarketPrice.crop_id, MarketPrice.location_id,
                     func.max(MarketPrice.observation_date).label("d"))
              .group_by(MarketPrice.crop_id, MarketPrice.location_id))
    if crop_id:
        latest = latest.where(MarketPrice.crop_id == crop_id)
    latest = latest.subquery()
    return (db.session.query(MarketPrice)
            .join(latest, (MarketPrice.crop_id == latest.c.crop_id)
                  & (MarketPrice.location_id == latest.c.location_id)
                  & (MarketPrice.observation_date == latest.c.d)))


# ---------------------------------------------------------------- crops
@bp.get("/crops")
def list_crops():
    q = query_text("q")
    category = query_text("category")
    query = db.session.query(Crop)
    if q:
        query = query.filter(Crop.name.ilike(f"%{q}%"))
    if category:
        query = query.filter(Crop.category == category)
    query = query.order_by(get_sort({"name": Crop.name, "category": Crop.category}, "name"))
    page = paginate(query, Crop.to_dict, default_per_page=50)
    ids = [c["id"] for c in page["items"]]
    if ids:
        stats = dict((r[0], r[1:]) for r in db.session.execute(
            select(MarketPrice.crop_id, func.count(MarketPrice.id), func.max(MarketPrice.observation_date),
                   func.count(distinct(MarketPrice.location_id)))
            .where(MarketPrice.crop_id.in_(ids)).group_by(MarketPrice.crop_id)).all())
        latest = {}
        for p in _latest_snapshot().filter(MarketPrice.crop_id.in_(ids)).all():
            latest.setdefault(p.crop_id, []).append(float(p.modal_price))
        for c in page["items"]:
            n, last, markets = stats.get(c["id"], (0, None, 0))
            vals = latest.get(c["id"], [])
            c.update(record_count=n, market_count=markets, latest_date=last.isoformat() if last else None,
                     latest_avg_modal_price=round(sum(vals) / len(vals), 2) if vals else None)
    page["categories"] = [r[0] for r in db.session.execute(select(distinct(Crop.category)).order_by(Crop.category))]
    return jsonify(page)


@bp.get("/crops/<int:crop_id>")
def get_crop(crop_id):
    crop = db.session.get(Crop, crop_id)
    if crop is None:
        raise NotFound("Crop not found.")
    latest = sorted(_latest_snapshot(crop_id).all(), key=lambda p: (p.location.state, p.location.market_name))
    count = db.session.scalar(select(func.count(MarketPrice.id)).where(MarketPrice.crop_id == crop_id))
    return jsonify({"crop": {**crop.to_dict(), "record_count": count},
                    "latest_by_market": [p.to_dict() for p in latest]})


# ---------------------------------------------------------------- markets
@bp.get("/markets")
def list_markets():
    state, district = query_text("state"), query_text("district")
    crop_id = query_int("crop_id")
    query = db.session.query(Location)
    if state:
        query = query.filter(Location.state == state)
    if district:
        query = query.filter(Location.district == district)
    if crop_id:
        query = query.filter(Location.id.in_(select(MarketPrice.location_id).where(MarketPrice.crop_id == crop_id)))
    query = query.order_by(Location.state, Location.district, Location.market_name)
    return jsonify(paginate(query, Location.to_dict, default_per_page=100))


# ---------------------------------------------------------------- prices
PRICE_SORTS = {"observation_date": MarketPrice.observation_date, "modal_price": MarketPrice.modal_price,
               "min_price": MarketPrice.min_price, "max_price": MarketPrice.max_price,
               "crop": Crop.name, "market": Location.market_name, "state": Location.state}


@bp.get("/prices")
def list_prices():
    f = {"crop_id": query_int("crop_id"), "location_id": query_int("location_id"),
         "q": query_text("q"), "state": query_text("state"), "district": query_text("district"),
         "date_from": query_date("date_from"), "date_to": query_date("date_to"), "is_demo": query_bool("is_demo")}
    latest_only = query_bool("latest")
    if f["date_from"] and f["date_to"] and f["date_from"] > f["date_to"]:
        raise ValidationError({"date_to": "Must be on or after date_from."})
    query = (_latest_snapshot() if latest_only else db.session.query(MarketPrice))
    query = query.join(Crop, MarketPrice.crop_id == Crop.id).join(Location, MarketPrice.location_id == Location.id)
    if f["crop_id"]:
        query = query.filter(MarketPrice.crop_id == f["crop_id"])
    if f["location_id"]:
        query = query.filter(MarketPrice.location_id == f["location_id"])
    if f["q"]:
        like = f"%{f['q']}%"
        query = query.filter(or_(Crop.name.ilike(like), Location.market_name.ilike(like)))
    if f["state"]:
        query = query.filter(Location.state == f["state"])
    if f["district"]:
        query = query.filter(Location.district == f["district"])
    if f["date_from"]:
        query = query.filter(MarketPrice.observation_date >= f["date_from"])
    if f["date_to"]:
        query = query.filter(MarketPrice.observation_date <= f["date_to"])
    if f["is_demo"] is not None:
        query = query.filter(MarketPrice.is_demo == f["is_demo"])
    query = query.order_by(get_sort(PRICE_SORTS, "-observation_date"), MarketPrice.id.desc())
    return jsonify(paginate(query, MarketPrice.to_dict))


@bp.get("/prices/<int:price_id>")
def get_price(price_id):
    p = db.session.get(MarketPrice, price_id)
    if p is None:
        raise NotFound("Price record not found.")
    return jsonify({"price": p.to_dict()})


@bp.get("/prices/history")
def price_history():
    crop_id = query_int("crop_id")
    if not crop_id:
        raise ValidationError({"crop_id": "This field is required."})
    crop = db.session.get(Crop, crop_id)
    if crop is None:
        raise NotFound("Crop not found.")
    location_id = query_int("location_id")
    date_from, date_to = query_date("date_from"), query_date("date_to")
    interval = request.args.get("interval", "week")
    if interval not in {"day", "week"}:
        raise ValidationError({"interval": "Must be 'day' or 'week'."})
    q = (select(MarketPrice.observation_date, MarketPrice.min_price, MarketPrice.max_price,
                MarketPrice.modal_price, MarketPrice.is_demo)
         .where(MarketPrice.crop_id == crop_id))
    if location_id:
        if db.session.get(Location, location_id) is None:
            raise NotFound("Market not found.")
        q = q.where(MarketPrice.location_id == location_id)
    if date_from:
        q = q.where(MarketPrice.observation_date >= date_from)
    if date_to:
        q = q.where(MarketPrice.observation_date <= date_to)
    rows = db.session.execute(q.order_by(MarketPrice.observation_date)).all()
    # Aggregate in Python so behaviour is identical on MySQL and SQLite.
    buckets = {}
    for d, lo, hi, modal, demo in rows:
        key = d if interval == "day" else d.fromordinal(d.toordinal() + (6 - d.weekday()))  # week ending Sunday
        b = buckets.setdefault(key, {"min": [], "max": [], "modal": [], "demo": False})
        b["min"].append(float(lo)); b["max"].append(float(hi)); b["modal"].append(float(modal))
        b["demo"] = b["demo"] or demo
    points = [{"date": k.isoformat(), "min_price": round(min(v["min"]), 2), "max_price": round(max(v["max"]), 2),
               "modal_price": round(sum(v["modal"]) / len(v["modal"]), 2), "observations": len(v["modal"]),
               "is_demo": v["demo"]} for k, v in sorted(buckets.items())]
    return jsonify({"crop": crop.to_dict(), "location_id": location_id, "interval": interval,
                    "aggregation": "mean modal price across markets" if not location_id else "mean modal price",
                    "points": points})


# ---------------------------------------------------------------- stats
@bp.get("/stats/summary")
def summary():
    total = db.session.scalar(select(func.count(MarketPrice.id))) or 0
    demo = db.session.scalar(select(func.count(MarketPrice.id)).where(MarketPrice.is_demo.is_(True))) or 0
    return jsonify({
        "crops": db.session.scalar(select(func.count(Crop.id))) or 0,
        "markets": db.session.scalar(select(func.count(Location.id))) or 0,
        "states": db.session.scalar(select(func.count(distinct(Location.state)))) or 0,
        "price_records": total,
        "demo_price_records": demo,
        "verified_price_records": total - demo,
        "predictions": db.session.scalar(select(func.count(Prediction.id))) or 0,
        "latest_observation_date": (lambda d: d.isoformat() if d else None)(
            db.session.scalar(select(func.max(MarketPrice.observation_date)))),
    })
