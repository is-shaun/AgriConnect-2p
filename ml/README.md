# AgriConnect ML

Crop-price estimation 1, 2 or 4 weeks ahead for one crop at one market.

| File | Purpose |
|---|---|
| `agriml/data.py` | CSV loading, validation and cleaning (shared with the API) |
| `agriml/features.py` | weekly series and leakage-safe features (shared with the API) |
| `agriml/modeling.py` | baselines, candidate models, chronological split, metrics |
| `agriml/predictor.py` | load an artifact and predict for one series |
| `generate_demo_data.py` | writes the **synthetic** demo CSV |
| `train.py` | full training run → `artifacts/price_model.joblib` + `.metrics.json` |
| `evaluate.py` | print stored metrics, or score a model on new CSV data |
| `predict.py` | command-line prediction from a CSV history |

## Commands

```bash
python ml/generate_demo_data.py                 # regenerate data/demo_market_prices.csv (deterministic, seed 42)
python ml/train.py                              # train on the demo CSV (labelled synthetic_demo)
python ml/train.py --csv real.csv --data-kind real
python ml/evaluate.py                           # stored validation and test metrics
python ml/evaluate.py --csv newer.csv --after 2026-10-20   # score on data the model has not seen
python ml/predict.py --commodity Onion --state Maharashtra --district Nashik --market Lasalgaon --horizon 2
```

Note: `evaluate.py --csv` on the same CSV used for training mostly scores in-sample rows (the deployed model is refit on all data); use `--after` with newer data for an honest check.

## Method

- **Unit of time**: weeks. Daily mandi data is irregular (holidays, no arrivals), so each crop/market series becomes a weekly mean modal price (week ending Sunday). Up to 2 missing weeks are forward-filled; longer gaps split the series so features never reach across them.
- **Features at week t** (only weeks ≤ t): price ratios to lags 1/2/4/8, ratios to 4- and 12-week moving averages, 4-week volatility of log changes, 4-week momentum, log price, week-of-year sin/cos, one-hot crop/state/market, and the horizon.
- **Target**: log(price at t+h / price at t). The predicted price is `price_t × exp(prediction)`. Only target weeks that were actually observed are used.
- **Split**: last 16 weeks = test, 16 before = validation, rest = train, purging rows whose target crosses into a later window.
- **Selection**: lowest validation MAE (in Rs/quintal) among naive last value, 4-week moving average, Ridge, RandomForest and HistGradientBoosting. A complex model is only chosen if it actually wins.
- **Reported**: validation table, held-out test MAE / RMSE / MAPE overall and per horizon, skill vs the best baseline, and the 10th–90th percentile of test errors per horizon (shown in the UI as the "typical range").
- **Minimum history**: 13 consecutive weeks for a prediction.

## Honesty rules built in
- The bundled data is synthetic; `train.py` refuses `--data-kind real` on it.
- The artifact records `data_kind`; the API labels every prediction from a non-real model as a demo estimate.
- Unknown crops/markets and short histories raise errors; nothing falls back to an invented number.
- A feature-version check stops an old artifact from being used with changed feature code.
