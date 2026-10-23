"""Export market prices from the database to the documented CSV format, e.g. to retrain
the model on everything that has been imported:

    python database/export_prices.py --out ml/data/db_export.csv --only-imported
    python ml/train.py --csv ml/data/db_export.csv --data-kind real
"""

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import Crop, Location, MarketPrice  # noqa: E402

COLUMNS = ["state", "district", "market", "commodity", "category", "unit", "arrival_date",
           "min_price", "max_price", "modal_price", "source"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only-imported", action="store_true", help="exclude demo records")
    args = ap.parse_args()
    app = create_app()
    n = 0
    with app.app_context(), open(args.out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(COLUMNS)
        q = (db.session.query(MarketPrice, Crop, Location).join(Crop).join(Location)
             .order_by(Crop.name, Location.state, Location.market_name, MarketPrice.observation_date))
        if args.only_imported:
            q = q.filter(MarketPrice.is_demo.is_(False))
        for p, c, loc in q.yield_per(5000):
            w.writerow([loc.state, loc.district, loc.market_name, c.name, c.category, c.unit,
                        p.observation_date.isoformat(), p.min_price, p.max_price, p.modal_price, p.source])
            n += 1
    print(f"Exported {n} rows to {args.out}")


if __name__ == "__main__":
    main()
