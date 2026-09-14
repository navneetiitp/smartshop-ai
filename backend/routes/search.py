from flask import Blueprint, jsonify, request
from ..ml.ai_score import score_dataframe
from ..utils.data_loader import get_dataframe
from ..utils.live_history import record_observations
from ..live_provider import is_configured, search_live
import pandas as pd
import re

search_bp = Blueprint("search", __name__)


def _safe_image(url) -> str:
    placeholder = "https://placehold.co/400x300/1e293b/94a3b8?text=No+Image"
    if not url or str(url).strip().lower() in ("", "nan", "none", "n/a", "not available"):
        return placeholder
    value = str(url).strip()
    return value if re.match(r"^https?://", value, re.I) else placeholder


def _static_search(query: str, website: str, sort_by: str, min_price: int, max_price: int, page: int, per_page: int):
    df = get_dataframe()
    if query:
        # Literal matching: user input is never interpreted as a regex.
        pattern = re.escape(query)
        mask = (
            df["product_name"].str.lower().str.contains(pattern, na=False, regex=True)
            | df["product_description"].str.lower().str.contains(pattern, na=False, regex=True)
        )
        df = df[mask]

    if website and website != "all":
        wanted = website.lower()
        df = df[df["website"].str.lower().str.contains(re.escape(wanted), na=False)]

    df = df[(df["price"] >= min_price) & (df["price"] <= max_price)]
    if df.empty:
        return {"results": [], "total": 0, "page": page, "pages": 0, "data_mode": "historical", "query": query}

    df = score_dataframe(df)
    sort_map = {
        "ai_score": ("ai_score", False),
        "price_asc": ("price", True),
        "price_desc": ("price", False),
        "rating": ("ratings_num", False),
    }
    sort_col, asc = sort_map.get(sort_by, ("ai_score", False))
    df = df.sort_values(sort_col, ascending=asc, na_position="last")

    total = len(df)
    pages = (total + per_page - 1) // per_page
    page = max(1, min(page, max(1, pages)))
    df_page = df.iloc[(page - 1) * per_page: page * per_page]

    results = []
    for _, row in df_page.iterrows():
        results.append({
            "id": int(row["id"]),
            "product_name": row["product_name"],
            "product_description": row["product_description"],
            "price": int(row["price"]),
            "currency": "INR",
            "ratings": row["ratings"],
            "ratings_num": float(row["ratings_num"]) if pd.notna(row["ratings_num"]) else None,
            "reviews": row["reviews"],
            "product_link": row["product_link"],
            "image_link": _safe_image(row["image_link"]),
            "website": row["website"],
            "date": str(row["date"]),
            "ai_score": float(row["ai_score"]),
            "value_score": float(row["ai_score"]),
            "data_source": "historical",
        })
    return {"results": results, "total": total, "page": page, "pages": pages, "data_mode": "historical", "query": query}


def _live_results(query: str, website: str, sort_by: str, min_price: int, max_price: int, page: int, per_page: int):
    payload = search_live(query or "laptop", limit=40, website=website)
    rows = payload["results"]

    rows = [r for r in rows if min_price <= r["price"] <= max_price]
    for row in rows:
        rating = row.get("ratings_num") or 0
        # Live result score is intentionally transparent: rating is the only
        # normalized quality signal we can safely infer from the feed itself.
        row["value_score"] = round(min(100.0, max(0.0, rating / 5.0 * 100.0)), 1)
        row["image_link"] = _safe_image(row.get("image_link"))

    if sort_by == "price_asc":
        rows.sort(key=lambda r: r["price"])
    elif sort_by == "price_desc":
        rows.sort(key=lambda r: r["price"], reverse=True)
    elif sort_by == "rating":
        rows.sort(key=lambda r: (r.get("ratings_num") or -1), reverse=True)
    else:
        rows.sort(key=lambda r: r.get("value_score", 0), reverse=True)

    record_observations(rows)
    total = len(rows)
    pages = (total + per_page - 1) // per_page
    page = max(1, min(page, max(1, pages))) if pages else 1
    page_rows = rows[(page - 1) * per_page: page * per_page]
    return {
        "results": page_rows,
        "total": total,
        "page": page,
        "pages": pages,
        "data_mode": "live",
        "provider": payload.get("provider"),
        "observed_at": payload.get("observed_at"),
        "query": payload.get("query", query),
    }


@search_bp.route("/search")
def search():
    query = request.args.get("q", "").strip()
    website = request.args.get("website", "all").strip()
    sort_by = request.args.get("sort", "ai_score")
    min_price = max(0, request.args.get("min_price", type=int, default=0))
    max_price = max(min_price, request.args.get("max_price", type=int, default=9999999))
    page = max(1, request.args.get("page", type=int, default=1))
    per_page = max(1, min(40, request.args.get("per_page", type=int, default=20)))

    if is_configured():
        try:
            return jsonify(_live_results(query, website, sort_by, min_price, max_price, page, per_page))
        except Exception as exc:
            # Do not hide the failure: return a clearly marked historical fallback.
            result = _static_search(query, website, sort_by, min_price, max_price, page, per_page)
            result["live_error"] = str(exc)
            result["data_mode"] = "historical_fallback"
            return jsonify(result)

    return jsonify(_static_search(query, website, sort_by, min_price, max_price, page, per_page))


@search_bp.route("/product/<int:product_id>")
def get_product(product_id):
    df = get_dataframe()
    df = score_dataframe(df)
    row = df[df["id"] == product_id]
    if row.empty:
        return jsonify({"error": "Product not found"}), 404
    row = row.iloc[0]
    return jsonify({
        "id": int(row["id"]),
        "product_name": row["product_name"],
        "product_description": row["product_description"],
        "price": int(row["price"]),
        "currency": "INR",
        "ratings": row["ratings"],
        "ratings_num": float(row["ratings_num"]) if pd.notna(row["ratings_num"]) else None,
        "reviews": row["reviews"],
        "product_link": row["product_link"],
        "image_link": _safe_image(row["image_link"]),
        "website": row["website"],
        "date": str(row["date"]),
        "ai_score": float(row["ai_score"]),
        "data_source": "historical",
    })
