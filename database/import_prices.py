"""Validate and import real market-price data from a CSV file.

    python database/import_prices.py path/to/prices.csv --dry-run      # validate only
    python database/import_prices.py path/to/prices.csv                # import
    python database/import_prices.py path/to/prices.csv --on-duplicate update

The CSV format is documented in docs/DATA_IMPORT.md. Invalid rows are listed with their
line numbers and are never written. Imported rows are stored with is_demo = false and
are shown as "Imported" in the UI; pass --demo only for synthetic/test files.
Exit code is 1 if any row was rejected, so the script can be used in pipelines.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app import create_app  # noqa: E402
from app.services.importer import import_prices  # noqa: E402
from app.services.providers import CsvFileProvider  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--dry-run", action="store_true", help="validate and report without saving")
    ap.add_argument("--on-duplicate", choices=["skip", "update"], default="skip")
    ap.add_argument("--demo", action="store_true", help="mark rows as demo data")
    ap.add_argument("--source", help="source label for rows without a 'source' column")
    ap.add_argument("--max-errors", type=int, default=50)
    args = ap.parse_args()
    app = create_app()
    with app.app_context():
        provider = CsvFileProvider(args.csv, is_demo=args.demo, default_source=args.source)
        report = import_prices(provider, dry_run=args.dry_run, on_duplicate=args.on_duplicate)
    d = report.to_dict(max_errors=args.max_errors)
    for e in d.pop("errors"):
        print(f"line {e['row']:>6}  {e['field']:<14} {e['message']}")
    print(("DRY RUN – nothing saved. " if args.dry_run else "") + json.dumps(d))
    sys.exit(1 if report.errors else 0)


if __name__ == "__main__":
    main()
