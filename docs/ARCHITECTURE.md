# Architecture and design decisions

```
 Browser ──► Vite dev server / reverse proxy (one origin) ──► Flask API (/api) ──► MySQL
   React SPA                                                   │
                                                               └──► ml/agriml (features + joblib model)
```

## Backend
- **App factory + blueprints** (`auth`, `catalog`, `predictions`, `account`). Business logic sits in `services/`; routes stay thin.
- **Validation** is explicit Python in `schemas/validators.py`. Each validator returns a fresh dict of whitelisted fields, which is what prevents mass assignment.
- **Errors** are raised as `APIError` subclasses and rendered by one handler into `{"error": {code, message, details}}`. DB errors roll back the session and are logged without leaking internals.
- **Money** uses `DECIMAL(12,2)`; CHECK constraints enforce positive prices and `min ≤ modal ≤ max`; a unique key on `(crop_id, location_id, observation_date)` makes imports idempotent.
- **Schema management**: Flask-Migrate migration in `backend/migrations`; `flask init-db` (create_all) as a quick alternative; `database/schema.sql` is generated from the models with the MySQL dialect for reference.
- **History aggregation** (`/api/prices/history`) buckets by week in Python rather than SQL so results are identical on MySQL and SQLite (tests).

## Authentication
JWT in an HttpOnly cookie plus a double-submit CSRF token, chosen over `Authorization: Bearer` tokens in localStorage so that an XSS bug can't exfiltrate the session. The trade-off is CSRF handling and the need for same-origin serving, both handled (Vite proxy in dev, reverse proxy in prod). Tokens are not revocable server-side before expiry (documented limitation).

## ML integration
`ml/agriml` is a plain package imported by both `ml/train.py` and the Flask `prediction_service`, so inference reuses the exact cleaning and feature functions from training (a test asserts API and offline predictions match). The artifact stores the sklearn pipeline (preprocessing + estimator) and metadata: feature version, horizons, supported series, validation/test metrics, residual bands and data kind. The service refuses artifacts with a different feature version, crops/markets not seen in training, and series with too little recent history, returning explicit error codes instead of guesses. The model file is reloaded automatically when it changes.

A prediction is labelled demo if the model was trained on synthetic data **or** the history used for it contains demo rows.

## Frontend
- `services/api.js`: Axios instance (credentials, CSRF header, normalised `ApiError`, global 401 handler).
- `context/AuthContext`: session state, including *why* a user was signed out (logout vs expiry) so the login page can say so.
- `hooks/useApi`: loading/error/data with abort on change, used by every data view; every view has loading, error-with-retry and empty states.
- Public data pages (markets, crops) render in the website shell for visitors and in the app shell for signed-in users.
- Design: forest/leaf greens on a green-tinted neutral, Bricolage Grotesque headings with Atkinson Hyperlegible body text (designed for legibility), a single expressive element (the chalkboard-style mandi price board), and mustard reserved exclusively for "demo data".
