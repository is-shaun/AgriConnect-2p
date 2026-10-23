"""Command-line prediction from a CSV history using a saved model.

    python ml/predict.py --commodity Onion --state Maharashtra --district Nashik \
        --market Lasalgaon --horizon 2

Uses the same feature code (agriml.features) as training and as the Flask API.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from agriml.data import load_price_csv  # noqa: E402
from agriml.predictor import PricePredictor  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", default=str(HERE / "data" / "demo_market_prices.csv"))
    ap.add_argument("--model", default=str(HERE / "artifacts" / "price_model.joblib"))
    ap.add_argument("--commodity", required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--district", required=True)
    ap.add_argument("--market", required=True)
    ap.add_argument("--horizon", type=int, required=True, help="weeks ahead")
    a = ap.parse_args()

    predictor = PricePredictor.load(a.model)
    df, _ = load_price_csv(a.csv)
    mask = ((df.commodity.str.lower() == a.commodity.lower()) & (df.state.str.lower() == a.state.lower())
            & (df.district.str.lower() == a.district.lower()) & (df.market.str.lower() == a.market.lower()))
    history = df.loc[mask, ["arrival_date", "modal_price"]]
    result = predictor.predict(history, a.commodity, a.state, a.district, a.market, a.horizon)
    if result["is_demo_model"]:
        print("NOTE: demo model trained on synthetic data – this is NOT a real market forecast.", file=sys.stderr)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
