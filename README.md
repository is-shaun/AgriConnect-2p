# AgriConnect

A full-stack agriculture platform for checking crop prices across Indian markets (mandis), following how they move, and getting a machine-learning estimate of where they may go in the next 1, 2 or 4 weeks.

- **Frontend:** React 19, Vite, React Router, Axios, Tailwind CSS v4, Recharts, Lucide icons
- **Backend:** Python 3, Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-JWT-Extended, Flask-CORS
- **Database:** MySQL 8 (via PyMySQL)
- **ML:** pandas, NumPy, scikit-learn, joblib

> **About the data.** The repository ships with a **synthetic demo dataset** so you can run everything end to end. Demo prices are invented by a stochastic generator, stored with `is_demo = true`, and labelled "Demo" everywhere in the UI. The bundled model is trained on that synthetic data, so its estimates say **nothing** about real markets. See [docs/DATA_IMPORT.md](docs/DATA_IMPORT.md) to load real, properly licensed market data.

---

## Contents

1. [Features](#features)
2. [Project structure](#project-structure)
3. [Quick start](#quick-start)
4. [Configuration](#configuration)
5. [API reference](#api-reference)
6. [Machine-learning pipeline](#machine-learning-pipeline)
7. [Security design](#security-design)
8. [Testing](#testing)
9. [Troubleshooting](#troubleshooting)
10. [Known limitations](#known-limitations)

---

## Features

**Pages**
- **Landing** with a live "mandi board" of the latest price per crop, feature overview, how-it-works, calls to action, footer.
- **Register / Log in / Log out** with client- and server-side validation, protected routes, "session expired" and "logged out" notices.
- **Dashboard**: summary metrics, demo-data notice, 12-month price trend chart with crop picker, popular / recently viewed crops, your recent estimates, latest-price table, quick links.
- **Market prices explorer**: search, filters (crop, state, district, market, date range, demo/imported, latest only), sortable columns, pagination, filters kept in the URL, min/modal/max prices with unit, date and source badge.
- **Price estimate**: crop → market (only markets with history) → horizon (from the model). Shows estimate, typical error range, expected change, history-vs-estimate chart, warnings, disclaimer, model accuracy, and your paginated estimate history.
- **Crops list** (grouped by category) and **crop details** (description, history chart by market and period, latest price per market, links to records and estimates).
- **Profile**: update name, email (requires current password) and password.
- **About**, **Contact** (validated, stored in DB, rate limited), **Privacy** and **Terms** (placeholders clearly marked for legal review), **404**.

**Backend**: modular blueprints, DB-backed queries everywhere, pagination / filtering / whitelisted sorting, consistent JSON errors, JWT-in-HttpOnly-cookie auth with CSRF protection, per-user prediction privacy, rate limiting, CSV import with row-level validation, provider interface for future data sources, health check.

**ML**: leakage-safe weekly features, chronological train/validation/test split with purging, two baselines plus three regressors compared on validation MAE, honest held-out test metrics, joblib artifact with metadata, the same feature code used for training and the API.

---

## Project structure

```
AgriConnect/
├── backend/
│   ├── app/
│   │   ├── __init__.py          app factory, CLI commands (init-db, seed-demo, import-prices)
│   │   ├── extensions.py        db, migrate, jwt, cors
│   │   ├── models/              User, Crop, Location, MarketPrice, Prediction, ContactMessage
│   │   ├── routes/              auth, catalog (crops/markets/prices/stats), predictions, account (users/contact/health)
│   │   ├── schemas/validators.py  request validation (whitelists fields → no mass assignment)
│   │   ├── services/            importer, data providers, prediction service (bridge to ml/)
│   │   └── utils/               errors, pagination, rate limiting
│   ├── migrations/              Flask-Migrate (Alembic) migrations
│   ├── tests/                   pytest suite
│   ├── config.py · run.py · requirements.txt · requirements-dev.txt · .env.example
├── frontend/
│   ├── src/
│   │   ├── components/ layouts/ pages/ context/ hooks/ services/ utils/
│   │   └── test/                Vitest + Testing Library tests
│   ├── index.html · vite.config.js · package.json · .env.example
├── ml/
│   ├── agriml/                  shared package: data cleaning, features, models, predictor
│   ├── data/demo_market_prices.csv   SYNTHETIC demo data (26,831 rows, 32 series)
│   ├── artifacts/               trained model goes here (created by train.py)
│   ├── generate_demo_data.py · train.py · evaluate.py · predict.py · README.md
│   └── tests/
├── database/
│   ├── schema.sql               MySQL DDL generated from the models (reference / manual setup)
│   ├── seed.py · import_prices.py · export_prices.py
├── docs/                        ARCHITECTURE.md · DATA_IMPORT.md · TESTING.md
├── pytest.ini
└── README.md
```

---

## Quick start

Prerequisites: **Python 3.11+**, **Node.js 20.19+ or 22+**, **MySQL 8.0+**.

All commands are run from the `AgriConnect/` folder unless noted. Windows users: use `py` instead of `python3` and `.venv\Scripts\activate` instead of `source .venv/bin/activate`.

### 1. Set up MySQL

```sql
-- in the mysql client as an admin user
CREATE DATABASE agriconnect CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'agri_user'@'localhost' IDENTIFIED BY 'choose-a-strong-password';
GRANT ALL PRIVILEGES ON agriconnect.* TO 'agri_user'@'localhost';
FLUSH PRIVILEGES;
```

### 2. Backend environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-dev.txt

cp backend/.env.example backend/.env
# edit backend/.env: set DATABASE_URL with your password, e.g.
# DATABASE_URL=mysql+pymysql://agri_user:choose-a-strong-password@127.0.0.1:3306/agriconnect?charset=utf8mb4
```

### 3. Create tables and load demo data

```bash
cd backend
flask --app run.py db upgrade        # applies migrations (or: flask --app run.py init-db)
cd ..
python database/seed.py              # loads the SYNTHETIC demo prices (about 30 s on MySQL)
```

### 4. Train the price model

```bash
python ml/train.py                   # ~15 s; writes ml/artifacts/price_model.joblib
```

### 5. Start the backend

```bash
cd backend
python run.py                        # http://127.0.0.1:5000  (check: /api/health)
```

### 6. Start the frontend (new terminal)

```bash
cd frontend
cp .env.example .env
npm install
npm run dev                          # http://localhost:5173
```

Open http://localhost:5173, create an account, and try the dashboard, market explorer and price estimate.

### Production build

```bash
cd frontend && npm run build         # outputs frontend/dist
cd ../backend && APP_ENV=production gunicorn -w 2 -b 127.0.0.1:5000 run:app
```
Serve `frontend/dist` and proxy `/api` to Gunicorn from the same origin (e.g. Nginx). Set `APP_ENV=production`, strong `SECRET_KEY` / `JWT_SECRET_KEY`, `JWT_COOKIE_SECURE=true` and HTTPS; the app refuses to start in production with weak secrets.

---

## Configuration

`backend/.env` (see `backend/.env.example`):

| Variable | Purpose |
|---|---|
| `APP_ENV` | `development`, `production` (or `testing`) |
| `DATABASE_URL` | SQLAlchemy URL, `mysql+pymysql://user:pass@host:3306/agriconnect?charset=utf8mb4` |
| `SECRET_KEY`, `JWT_SECRET_KEY` | Random ≥ 32 chars, required in production: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `CORS_ORIGINS` | Exact frontend origin(s), comma separated |
| `JWT_COOKIE_SECURE` | `true` in production (HTTPS), defaults to `false` in development |
| `JWT_ACCESS_HOURS` | Session length (default 8) |
| `MODEL_PATH` | Model artifact (default `ml/artifacts/price_model.joblib`) |
| `RATE_LIMIT_ENABLED` | `true` by default |
| `TEST_DATABASE_URL` | Optional: run tests against MySQL |

`frontend/.env`: `VITE_API_BASE_URL` (default `/api`) and `VITE_BACKEND_URL` (Vite dev proxy target, default `http://127.0.0.1:5000`).

---

## Machine-learning pipeline

Details in [ml/README.md](ml/README.md). In short:

1. **Load and clean** the CSV: bad dates, non-numeric or non-positive prices, `min > modal > max` violations and duplicates are dropped and counted, never repaired.
2. **Weekly series** per crop and market (mean modal price, week ending Sunday; gaps of up to 2 weeks bridged, longer gaps split the series).
3. **Features** use only data up to the anchor week: lag ratios (1, 2, 4, 8 weeks), 4- and 12-week moving-average ratios, 4-week volatility and momentum, log price level, week-of-year (sin/cos), crop/state/market (one-hot), horizon.
4. **Target**: `log(price[t+h] / price[t])`, h ∈ {1, 2, 4} weeks; the target week must be a real observation.
5. **Chronological split**: train / last-16-week validation / last-16-week test, with rows whose target falls in a later window purged.
6. **Model selection** on validation MAE among: naive last value, 4-week moving average, Ridge, Random Forest, HistGradientBoosting.
7. **Honest test metrics**: the winner is refit on train+validation and scored on the test weeks against the best baseline; then refit on all data and saved with joblib together with its metadata.

Results on the bundled **synthetic** data (Rs/quintal):

| Model (validation) | MAE | RMSE | MAPE |
|---|---|---|---|
| Naive last value (baseline) | 105.0 | 232.6 | 3.89% |
| 4-week moving average (baseline) | 145.4 | 315.5 | 5.38% |
| Ridge | 107.1 | 243.6 | 3.87% |
| Random forest | 99.1 | 208.2 | 3.69% |
| **HistGradientBoosting (selected)** | **97.0** | **195.3** | **3.69%** |

Held-out test: MAE 102.6 vs 114.3 for the naive baseline (10.3% better); by horizon MAE 70 / 102 / 144 for 1 / 2 / 4 weeks. These numbers describe how well the model fits the generator's synthetic patterns, **not** real-world forecasting accuracy. R² is deliberately not reported: pooled across crops whose price levels differ around 5×, it mostly measures between-crop variance and would overstate skill.

---

## Testing

```bash
# backend + ML (from AgriConnect/) — uses in-memory SQLite by default
python -m pytest

# same suite against MySQL (create an empty agriconnect_test database first)
TEST_DATABASE_URL="mysql+pymysql://agri_user:pw@127.0.0.1:3306/agriconnect_test?charset=utf8mb4" python -m pytest

# frontend
cd frontend && npm test
```

What was actually run while building this project, and what was not, is listed in [docs/TESTING.md](docs/TESTING.md).

---

## Known limitations

- **No real market data is included.** Everything bundled is synthetic and labelled as such. Importing a genuine, licensed dataset is described in [docs/DATA_IMPORT.md](docs/DATA_IMPORT.md); no live data feed, scraper or API key is included.
- The demo model's accuracy reflects synthetic data only. Retrain with `--data-kind real` on genuine data and re-check the validation report before trusting estimates.
- The contact form stores messages in the database; no email is sent (no mail service credentials).
- Privacy and Terms pages are placeholders that need legal review.
- No admin interface; there is a `role` column (`user`/`admin`) ready for one.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for design decisions.
