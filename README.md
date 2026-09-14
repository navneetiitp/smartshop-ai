# SmartShop AI — Laptop Price Intelligence

A Flask + JavaScript laptop price intelligence platform that combines **live Google Shopping results**, historical catalog data, transparent value scoring, cross-store comparison, and conservative price forecasting.

SmartShop AI is designed to distinguish clearly between **real-time provider observations** and **historical catalog data** rather than presenting old or generated prices as current.

---

## 🚀 Features

- 🔴 **Live Google Shopping results** through SerpApi when `SERPAPI_KEY` is configured.
- 🇮🇳 **India-focused localization** by default:
  - `gl=in`
  - `hl=en`
  - `google.co.in`
- 🔎 Search across laptop listings using the user's query.
- 🏪 **Store-aware live search** for Amazon, Flipkart, BestBuy, and eBay when supported by the provider.
- 🔄 Search race protection so an older request cannot overwrite a newer search.
- 💰 Price sorting and price-range filtering.
- ⭐ Rating-based sorting and quality signals.
- 📄 Pagination for large result sets.
- 📊 Transparent **Value Score** for historical catalog listings.
- 🟢 Transparent **Live Quality Score** for live shopping listings.
- ⚖️ Cross-store product comparison using product identity matching.
- 📈 Conservative price forecasting using only real observations.
- 🚫 No synthetic prices or random warm-up data.
- 🕒 Five-minute caching for identical live searches.
- 💾 Local SQLite storage for real live-price observations.
- 🛡️ Explicit historical fallback when the live provider is unavailable.
- 🔐 API keys are kept outside the repository using environment variables.

---

## 🧠 How SmartShop AI Works

SmartShop AI operates in two main data modes.

### Historical Mode

The project includes a bundled laptop catalog containing historical observations.

The bundled dataset is **not presented as current market data**. Its latest bundled observations are from **November 2024**, and the application preserves the original historical timestamps.

When live shopping data is unavailable, the application clearly labels the results as **historical fallback data**.

### Live Shopping Mode

When `SERPAPI_KEY` is configured, SmartShop AI requests current Google Shopping results through SerpApi.

The application uses provider information such as:

- Product title
- Retailer/source
- Price
- Extracted price
- Rating
- Review count
- Product thumbnail
- Product link

Live searches are cached for **5 minutes** to reduce unnecessary provider requests.

> **Important:** Live Shopping data is a provider observation and is not a guarantee of the final checkout price. Seller, stock, shipping, taxes, discounts, and availability may change on the destination website.

---

## 📊 Scoring

### Value Score

Historical catalog products use a deterministic **Value Score** from 0–100.

It considers factors such as:

- Price competitiveness
- Product rating
- Review signal

The Value Score is a transparent calculation performed by the application. It is **not a claim of an external AI-generated rating**.

### Live Quality Score

Live listings use a separate **Live Quality Score**.

It is derived from the live provider's rating information when available and is intentionally kept separate from the historical Value Score.

This prevents historical catalog scoring logic from being incorrectly presented as a real-time AI judgment.

---

## 📈 Price Forecasting

SmartShop AI uses machine-learning-based regression for conservative price forecasting.

Forecasting uses **only real price observations collected by the application**.

The system requires:

- At least **7 real observations**
- Observations spanning at least **5 distinct dates**

Multiple listings collected during the same observation period are not treated as independent days of price history.

If insufficient real history exists:

- The latest real current price is shown when available.
- Prediction fields display `N/A`.
- The system does not invent prices to make a forecast possible.

This design intentionally prioritizes **data integrity over producing a prediction from insufficient data**.

---

## 🏪 Cross-Store Comparison

The comparison system attempts to identify the same or closely matching laptop across different retailers.

It uses product identity information rather than requiring every retailer listing to have exactly the same title.

For live products, the selected live listing can also be preserved during comparison.

Because retailer inventories change continuously, a particular product may not be available from every store at the same moment.

---

## 🔄 Data Flow

```text
User Search
     │
     ▼
SmartShop AI
     │
     ├─────────────── Historical Catalog
     │
     │
     └─────────────── SerpApi
                         │
                         ▼
                  Google Shopping
                         │
                         ▼
                 Live Product Data
                         │
                         ▼
                  SmartShop AI UI
                         │
                         ├── Value / Quality Score
                         ├── Comparison
                         └── Real-history Forecast
