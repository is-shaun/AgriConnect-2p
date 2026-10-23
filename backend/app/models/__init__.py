"""SQLAlchemy models. Prices use DECIMAL(12, 2); all timestamps are stored in UTC."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Index, UniqueConstraint
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db

PRICE = db.Numeric(12, 2)


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _money(value):
    return float(value) if value is not None else None


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (CheckConstraint("role IN ('user', 'admin')", name="ck_users_role"),)

    predictions = db.relationship("Prediction", back_populates="user", lazy="dynamic")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password, method="scrypt")

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "email": self.email, "role": self.role,
                "created_at": self.created_at.isoformat() + "Z"}


class Crop(db.Model):
    __tablename__ = "crops"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    category = db.Column(db.String(60), nullable=False, index=True)
    description = db.Column(db.Text)
    unit = db.Column(db.String(30), nullable=False, default="Rs/quintal")

    prices = db.relationship("MarketPrice", back_populates="crop", lazy="dynamic")

    def to_dict(self):
        return {"id": self.id, "name": self.name, "category": self.category,
                "description": self.description, "unit": self.unit}


class Location(db.Model):
    __tablename__ = "locations"
    id = db.Column(db.Integer, primary_key=True)
    state = db.Column(db.String(80), nullable=False)
    district = db.Column(db.String(80), nullable=False)
    market_name = db.Column(db.String(120), nullable=False)

    __table_args__ = (
        UniqueConstraint("state", "district", "market_name", name="uq_location"),
        Index("ix_locations_state_district", "state", "district"),
    )

    def to_dict(self):
        return {"id": self.id, "state": self.state, "district": self.district, "market_name": self.market_name}


class MarketPrice(db.Model):
    __tablename__ = "market_prices"
    id = db.Column(db.BigInteger().with_variant(db.Integer, "sqlite"), primary_key=True)
    crop_id = db.Column(db.Integer, db.ForeignKey("crops.id", ondelete="RESTRICT"), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False)
    observation_date = db.Column(db.Date, nullable=False)
    min_price = db.Column(PRICE, nullable=False)
    max_price = db.Column(PRICE, nullable=False)
    modal_price = db.Column(PRICE, nullable=False)
    source = db.Column(db.String(255), nullable=False)
    is_demo = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    crop = db.relationship("Crop", back_populates="prices")
    location = db.relationship("Location")

    __table_args__ = (
        UniqueConstraint("crop_id", "location_id", "observation_date", name="uq_price_observation"),
        CheckConstraint("min_price > 0 AND max_price > 0 AND modal_price > 0", name="ck_price_positive"),
        CheckConstraint("min_price <= modal_price AND modal_price <= max_price", name="ck_price_order"),
        Index("ix_prices_crop_loc_date", "crop_id", "location_id", "observation_date"),
        Index("ix_prices_date", "observation_date"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "crop": {"id": self.crop.id, "name": self.crop.name, "unit": self.crop.unit},
            "location": self.location.to_dict(),
            "observation_date": self.observation_date.isoformat(),
            "min_price": _money(self.min_price),
            "max_price": _money(self.max_price),
            "modal_price": _money(self.modal_price),
            "unit": self.crop.unit,
            "source": self.source,
            "is_demo": self.is_demo,
        }


class Prediction(db.Model):
    __tablename__ = "predictions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    crop_id = db.Column(db.Integer, db.ForeignKey("crops.id"), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey("locations.id"), nullable=False)
    horizon_weeks = db.Column(db.SmallInteger, nullable=False)
    base_date = db.Column(db.Date, nullable=False)
    prediction_date = db.Column(db.Date, nullable=False)
    base_price = db.Column(PRICE, nullable=False)
    predicted_price = db.Column(PRICE, nullable=False)
    range_low = db.Column(PRICE)
    range_high = db.Column(PRICE)
    model_version = db.Column(db.String(80), nullable=False)
    is_demo = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)

    user = db.relationship("User", back_populates="predictions")
    crop = db.relationship("Crop")
    location = db.relationship("Location")

    __table_args__ = (
        CheckConstraint("predicted_price > 0", name="ck_prediction_positive"),
        CheckConstraint("horizon_weeks BETWEEN 1 AND 52", name="ck_prediction_horizon"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "crop": {"id": self.crop.id, "name": self.crop.name, "unit": self.crop.unit},
            "location": self.location.to_dict(),
            "horizon_weeks": self.horizon_weeks,
            "base_date": self.base_date.isoformat(),
            "prediction_date": self.prediction_date.isoformat(),
            "base_price": _money(self.base_price),
            "predicted_price": _money(self.predicted_price),
            "typical_range": ({"low": _money(self.range_low), "high": _money(self.range_high)}
                              if self.range_low is not None else None),
            "unit": self.crop.unit,
            "model_version": self.model_version,
            "is_demo": self.is_demo,
            "created_at": self.created_at.isoformat() + "Z",
        }


class ContactMessage(db.Model):
    __tablename__ = "contact_messages"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)


__all__ = ["User", "Crop", "Location", "MarketPrice", "Prediction", "ContactMessage", "utcnow"]
