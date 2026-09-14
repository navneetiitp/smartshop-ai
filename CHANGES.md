# SmartShop AI — Final release pass

- Added optional SerpApi Google Shopping live search with India localization.
- Added 5-minute in-memory caching to reduce repeated provider requests.
- Added stale-request protection so an older search cannot overwrite a newer query.
- Made search submission explicit to the active search box.
- Added retailer-aware live search for Amazon, Flipkart, BestBuy, and eBay, including seller/domain aliases.
- Reworked comparison matching around brand/model identity instead of exact long product titles.
- Added retailer-targeted comparison discovery when one store dominates the first Shopping page.
- Preserved the selected live listing during comparison, including transient provider failures.
- Prevented history-storage errors from turning a valid live comparison into a failed request.
- Fixed forecast empty-state behavior so a real current price is shown while prediction fields remain `N/A` when history is insufficient.
- Kept forecasting free of synthetic/random prices.
- Validated historical external links to HTTP(S) URLs only.
- Improved API error handling so unexpected API failures remain JSON-shaped.
- Removed misleading AI wording from deterministic scoring and sorting labels.
- Explicitly distinguish live, historical, and fallback modes.
- Removed secrets, virtual environments, Python caches, and runtime SQLite data from the release archive.
- Added release/security documentation for GitHub publishing.
