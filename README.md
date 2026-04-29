# ⚡ SmartShop AI — Laptop Price Intelligence

A full-stack ML web application for comparing laptop prices across **Amazon**, **Flipkart**, and **BestBuy**, with AI scoring, AI summaries, and future price prediction.

---

## 📁 Folder Structure

```
smartshop/
├── requirements.txt
├── backend/
│   ├── app.py                    # Flask entry point
│   ├── data/
│   │   └── products.csv          # Your dataset (3,370 laptops)
│   ├── ml/
│   │   ├── ai_score.py           # AI Score calculation (weighted ML)
│   │   ├── summarizer.py         # AI Summary generation
│   │   └── predictor.py          # Linear Regression price forecasting
│   ├── routes/
│   │   ├── search.py             # GET /api/search
│   │   ├── compare.py            # GET /api/compare
│   │   ├── predict.py            # GET /api/predict
│   │   └── summary.py            # GET /api/summary/<id>
│   └── utils/
│       └── data_loader.py        # CSV loading + data cleaning
└── frontend/
    ├── templates/
    │   ├── index.html            # Home page
    │   └── product.html          # Product detail page
    └── static/
        ├── css/
        │   └── style.css         # Full dark-theme UI
        └── js/
            ├── app.js            # Search, compare, forecast logic
            └── product.js        # Product detail page logic
```

---

## 🚀 Setup & Run

### 1. Install Python dependencies
```bash
cd smartshop
pip install -r requirements.txt
```

### 2. Run Flask server
```bash
cd backend
python app.py
```

### 3. Open in browser
```
http://localhost:5000
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/search?q=dell&website=amazon&sort=ai_score&page=1` | Search + filter + paginate |
| GET | `/api/product/<id>` | Single product detail |
| GET | `/api/compare?name=Dell XPS 15` | Cross-site price comparison |
| GET | `/api/predict?name=HP TPN-Q279&months=3` | ML price forecast |
| GET | `/api/summary/<id>` | AI-generated text summary |

### Filter parameters for `/api/search`:
- `q` — search query
- `website` — `all`, `amazon`, `flipkart`, `bestbuy`
- `sort` — `ai_score`, `price_asc`, `price_desc`, `rating`
- `min_price`, `max_price` — INR price range
- `page`, `per_page` — pagination

---

## 🤖 ML Features

### AI Score (0–100)
Weighted combination of:
- **Rating score** (35%) — numeric 1–5 star rating
- **Review sentiment** (25%) — text review mapped to 1–5 scale
- **Price competitiveness** (30%) — how cheap vs. same product on other sites
- **Recency** (10%) — how recent the listing date is

### AI Summary
Parses `product_description` to extract specs (Processor, RAM, Storage, OS, Display) and generates a human-readable summary with rating label, review sentiment, and AI score context.

### Price Prediction
Uses `sklearn.linear_model.LinearRegression` trained on:
- Days since earliest listing date
- Website encoding (LabelEncoder)

Outputs: current avg price, predicted price in N months, % change, and trend chart data.

---

## 📊 Dataset Details

| Field | Notes |
|-------|-------|
| `ratings` | String — `"4.5"` or `"Not Available"` → cleaned to float |
| `reviews` | Sentiment text — mapped to 1–5 score |
| `price` | Float (INR) — range ₹3,734 to ₹5,06,299 |
| `website` | Amazon · Flipkart · BestBuy |
| `image_link` | Mostly `"Not Available"` → replaced with placeholder |
| `date` | Datetime string → parsed for recency scoring |

---

## 🎨 UI Features
- Dark theme inspired by Flipkart/Amazon
- Product grid with AI Score bars
- Review sentiment tags (Excellent / Very Good / Average / Poor)
- Price comparison modal (cross-site)
- Price forecast modal with bar chart
- Product detail page with specs table + AI summary
- Pagination, filters, sort controls
- Fully responsive
