# SmartShop AI — Laptop Price Intelligence

A Flask + JavaScript laptop price intelligence app with live Google Shopping search, store filtering, sorting, transparent value scoring, price comparison, and conservative price forecasting.

## Features

- Live Google Shopping results through SerpApi when `SERPAPI_KEY` is configured.
- India localization by default (`gl=in`, `hl=en`, `google.co.in`).
- Search race protection so an older request cannot overwrite a newer query.
- Store-aware live search for Amazon, Flipkart, BestBuy, and eBay.
- Price and rating sorting, price-range filtering, and pagination.
- Transparent **Value Score** for historical catalog data and **Live Quality Score** for live listings.
- Cross-store comparison that searches by product identity and preserves the selected live listing.
- Price forecasting only after enough real observations are collected; no synthetic prices or random warm-up data.
- Explicit historical fallback when the live provider fails.

## Data modes

### Historical catalog
The bundled CSV is historical (latest bundled observations are from November 2024). The UI labels it as historical and never changes those timestamps to make them look current.

### Live shopping mode
When `SERPAPI_KEY` is configured, searches request Google Shopping results through SerpApi. The app uses provider fields such as title, source, price, extracted price, rating, reviews, thumbnail, and product link.

Identical live searches are cached for 5 minutes to reduce repeated provider requests. Live observations are stored locally in SQLite for future forecasting. If the provider fails, the UI explicitly identifies the historical fallback instead of calling it live.

> Live Shopping data is a provider observation, not a guarantee of final checkout price. Seller, stock, shipping, taxes, and availability can change on the destination site.

## Configure live mode

1. Create a SerpApi account and API key.
2. Copy `.env.example` to `.env`.
3. Put your own key in `.env`:

```text
SERPAPI_KEY=your_real_key_here
SERPAPI_GL=in
SERPAPI_HL=en
SERPAPI_GOOGLE_DOMAIN=google.co.in
FLASK_DEBUG=false
```

The application loads the project-root `.env` automatically. **Never commit `.env` or a real API key to GitHub.**

## Windows setup

### Option A — automatic

Double-click:

```text
START_WINDOWS.bat
```

### Option B — terminal

From the project root:

```powershell
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
cd backend
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

Health check:

```text
http://127.0.0.1:5000/api/health
```

Expected live configuration:

```json
{"status":"ok","provider_configured":true,"data_mode":"live_configured"}
```

## API

- `GET /api/search?q=dell` — search, store filters, sorting, price filters, and pagination
- `GET /api/product/<id>` — bundled historical catalog detail
- `GET /api/compare?name=...` — relevant live cross-store comparison
- `GET /api/predict?name=...&current_price=...` — forecast when enough real history exists
- `GET /api/summary/<id>` — historical product summary
- `GET /api/meta` — catalog/provider/history status
- `GET /api/health` — application health

## Scoring

The historical catalog uses a deterministic **Value Score**, not a claim of an external AI rating. It considers price competitiveness, rating, and review signal. Live listings use a transparent **Live Quality Score** derived from the live provider rating when available.

## Forecasting

Forecasting uses only real price observations. It requires at least 7 observations across 5 distinct dates. Multiple listings collected during the same observation period are not treated as independent days of history. Until enough real history exists, the UI shows the latest real current price and `N/A` for prediction fields.

## GitHub / security

Before pushing the repository:

- Keep `.env` untracked.
- Do not commit `venv/`, `__pycache__/`, `*.pyc`, or SQLite runtime databases.
- Do not paste API keys into README files, screenshots, source code, or issues.
- If an API key has ever been committed or shared, rotate it before publishing the repository.

The repository intentionally contains `.env.example`, not a real credential.
