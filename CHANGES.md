# SmartShop AI — Changes

## September 2026 — Live Price Intelligence Update

### Added

- Added live Google Shopping price retrieval through SerpApi.
- Added India-focused Google Shopping localization.
- Added live retailer-aware searches for Amazon, Flipkart, BestBuy, and eBay where supported by provider results.
- Added five-minute in-memory caching for identical live searches.
- Added local SQLite storage for real live-price observations.
- Added cross-store comparison using product identity matching.
- Added conservative price forecasting based only on real observations.
- Added explicit health and metadata endpoints for application/provider status.
- Added Render deployment support through Gunicorn.
- Added `.env.example` for safe API-key configuration.

### Changed

- Historical catalog data is now clearly separated from live shopping data.
- Historical prices and timestamps are never presented as current.
- Replaced misleading AI-style historical scoring with a transparent deterministic **Value Score**.
- Added a separate **Live Quality Score** for live listings.
- Search results now explicitly identify whether data is live or historical fallback.
- Search requests now prevent stale asynchronous responses from overwriting newer searches.
- Product comparison now preserves the selected live listing when possible.
- Forecasting now uses daily aggregation so multiple listings from the same observation period are not incorrectly treated as separate days.
- Forecasting now requires sufficient real price history before producing predictions.
- Forecast results show the latest real current price and `N/A` prediction fields when history is insufficient.
- Improved product-link validation and retailer normalization.
- Improved error handling for live-provider failures.
- Improved API error responses.
- Added responsive frontend behavior and cache-busting for static assets.
- Updated backend imports for package-based deployment with Gunicorn.

### Removed

- Removed synthetic/random price history generation.
- Removed random warm-up observations.
- Removed misleading claims that generated values represented real market history.
- Removed unnecessary open CORS configuration.

### Security

- `.env` is excluded from Git.
- Real API keys are not included in the repository.
- Virtual environments, Python cache files, and runtime SQLite databases are excluded from Git.
- `.env.example` contains configuration placeholders only.
- If an API key has previously been exposed or committed, it should be rotated before publication.

### Deployment

The production application can be started with:

```text
gunicorn backend.app:app
