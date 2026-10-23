# Test report

Recorded on 23 October 2026 in the build environment. That environment had **no access to PyPI or the npm registry and no MySQL server**, which shaped what could be run. Everything below states what actually ran.

## Ran and passed

### Backend + ML: `python -m pytest` — 59 passed (≈25 s)
Database: in-memory SQLite (the configured default for tests). Python 3.13, Flask 3.1, Flask-SQLAlchemy 3.1.1, SQLAlchemy 2.0.43, Flask-JWT-Extended 4.7.1, Flask-Migrate 4.1, pandas 3.0, scikit-learn 1.9.

| File | Tests | Covers |
|---|---|---|
| `backend/tests/test_auth.py` | 11 | register (hashing, cookies), duplicate email, validation, role mass-assignment blocked, non-JSON body, login success / wrong password / unknown email (same message), `/me` protection, CSRF required for writes, tampered token, login rate limit (429 on 11th try) |
| `backend/tests/test_catalog.py` | 8 | crop list stats/search/category, crop detail + 404, market filters, price pagination/sorting/filters (district, dates, search, latest, is_demo), invalid query params (422), price detail + history (weekly/daily, date filter), summary, health |
| `backend/tests/test_predictions.py` | 16 | public model info, auth required, successful model-generated prediction labelled demo with range/dates/history, deterministic output, API result equals offline `ml/` pipeline, users can't read others' predictions, 6 input-validation cases, unknown crop/market (404), unsupported series (422), insufficient history (422), supported series without rows, missing model (503), corrupt model (503) |
| `backend/tests/test_account_and_data.py` | 14 | profile get/update, role escalation blocked, current password required for email/password change, unique email, contact success + validation, all tables created, schema compiles for the MySQL dialect, DB CHECK constraint on price order, CSV import row-level errors + idempotency, dry run + update mode, missing columns, `init-db` / `seed-demo` CLI |
| `ml/tests/test_pipeline.py` | 10 | cleaning drops invalid rows (no invented values), required columns, **no future leakage** (perturbing future prices leaves past features identical), exact-horizon observed targets, split has no overlap/look-ahead, minimum history, long gaps split series, train→save→load→predict round trip, missing/corrupt artifacts |

### Database tooling (against SQLite)
`flask db upgrade` (Alembic migration), `python database/seed.py` (26,831 demo rows), `import_prices.py --dry-run` (row-level errors reported), `export_prices.py` — all ran successfully. `database/schema.sql` is generated from the models with SQLAlchemy's MySQL dialect.

### Model training: `python ml/train.py` — completed
Validation MAE (Rs/quintal): naive 105.0, moving average 145.4, ridge 107.1, random forest 99.1, HistGradientBoosting 97.0 (selected). Held-out test MAE 102.6 vs 114.3 for the naive baseline. Synthetic data only.

### Frontend unit tests — 9 passed
`src/test/format.test.js` (5) and `src/test/validation.test.js` (4), executed with Node's built-in test runner through a small compatibility shim for the `vitest` API, because Vitest itself could not be installed.

### Frontend build and browser end-to-end — 14/14 flows passed, 0 console errors
Because Vite could not be installed, the real `src/` code was bundled with esbuild against the **actual source code** of React 19, React Router 7.9, Recharts 3.2, Redux Toolkit, Immer, Reselect and Lucide icons (cloned from GitHub), and the CSS was compiled with Tailwind CSS 4's own compiler. That bundle was served with an `/api` proxy to the running Flask backend and driven in headless Chromium (Playwright):

landing page with live price board · protected-route redirect · registration validation · registration → dashboard (summary, chart, table) · explorer filters, sorting and pagination · explorer empty state · crops list → crop detail with chart · prediction workflow with chart and history · prediction form validation · profile update and password validation · logout notice, wrong-password error, re-login · contact form validation and submission · about / privacy / 404 · mobile (390 px) layout without horizontal overflow and mobile menu.

Rate limiting was also observed working in the browser (contact form returned 429 after repeated runs).

## Not run here — please run on your machine
- **`npm run build` with Vite** and **`npm test` with Vitest** (including `LoginPage.test.jsx`, which needs jsdom). The code is written for them and the equivalent esbuild bundle passed, but the Vite build itself was not executed.
- **MySQL**: the app, migrations and tests were not executed against a live MySQL server. To verify:
  ```bash
  TEST_DATABASE_URL="mysql+pymysql://agri_user:pw@127.0.0.1:3306/agriconnect_test?charset=utf8mb4" python -m pytest
  ```
- Dependency versions in `requirements.txt` / `package.json` are minimum versions known to be API-compatible with what was tested; `pip install` / `npm install` were not run from the registries.
