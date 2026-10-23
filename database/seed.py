"""Create tables (if needed) and load the SYNTHETIC demo dataset.

    cd AgriConnect
    python database/seed.py                 # uses DATABASE_URL from backend/.env
    python database/seed.py --reset         # drop + recreate all tables first (destroys data!)

Every seeded price record has is_demo = true and a source string beginning with "DEMO",
and the UI labels them as demo data.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app import DEMO_CSV, create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.services.importer import import_prices  # noqa: E402
from app.services.providers import CsvFileProvider  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reset", action="store_true", help="drop and recreate all tables first")
    ap.add_argument("--csv", default=str(DEMO_CSV))
    args = ap.parse_args()
    app = create_app()
    with app.app_context():
        if args.reset:
            db.drop_all()
        db.create_all()
        report = import_prices(CsvFileProvider(args.csv, is_demo=True))
        print(f"Demo data: {report.inserted} inserted, {report.skipped_duplicates} already present, "
              f"{report.crops_created} crops and {report.locations_created} markets created, "
              f"{len(report.errors)} invalid rows.")


if __name__ == "__main__":
    main()
