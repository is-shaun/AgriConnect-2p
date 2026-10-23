from __future__ import annotations

from flask import request

from .errors import ValidationError

MAX_PER_PAGE = 100


def get_page_args(default_per_page: int = 20) -> tuple[int, int]:
    errors = {}
    try:
        page = int(request.args.get("page", 1))
        if page < 1:
            raise ValueError
    except ValueError:
        errors["page"] = "Must be a positive integer."
        page = 1
    try:
        per_page = int(request.args.get("per_page", default_per_page))
        if not 1 <= per_page <= MAX_PER_PAGE:
            raise ValueError
    except ValueError:
        errors["per_page"] = f"Must be an integer between 1 and {MAX_PER_PAGE}."
        per_page = default_per_page
    if errors:
        raise ValidationError(errors)
    return page, per_page


def paginate(query, serializer, default_per_page: int = 20) -> dict:
    page, per_page = get_page_args(default_per_page)
    total = query.order_by(None).count()
    items = query.limit(per_page).offset((page - 1) * per_page).all()
    return {
        "items": [serializer(i) for i in items],
        "pagination": {"page": page, "per_page": per_page, "total": total,
                       "pages": max(1, -(-total // per_page))},
    }


def get_sort(allowed: dict, default: str):
    """Map ?sort=field or ?sort=-field onto a whitelisted SQLAlchemy column."""
    raw = request.args.get("sort", default)
    desc = raw.startswith("-")
    key = raw.lstrip("-")
    if key not in allowed:
        raise ValidationError({"sort": f"Must be one of: {', '.join(sorted(allowed))} (prefix with - for descending)."})
    col = allowed[key]
    return col.desc() if desc else col.asc()
